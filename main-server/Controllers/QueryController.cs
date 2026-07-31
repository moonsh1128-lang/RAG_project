using MainServer.Clients;
using MainServer.Models;
using MainServer.Services;
using Microsoft.AspNetCore.Mvc;

namespace MainServer.Controllers;

[ApiController]
[Route("query")]
public sealed class QueryController(
    RagServerClient ragServer, LlmServerClient llmServer, DbServerClient dbServer, ChunkAssemblyStore chunkStore)
    : ControllerBase
{
    private const int TopK = 1; // RagServer가 현재 top_k=1로 검색함

    [HttpPost]
    public async Task<IActionResult> PostAsync(QueryChunkRequest chunk, CancellationToken ct)
    {
        // MainServer 자체 재조립 — DB에는 청크가 아니라 완성된 질문 하나로 저장하기 위함
        var assembly = chunkStore.GetOrAdd(chunk.SessionId);
        assembly.Add(
            chunk.RequestNumber, chunk.MessageChunk, chunk.FinalRequestNumber,
            chunk.MessageCount, chunk.History);

        // 청크는 그대로 RagServer에도 전달 — RagServer가 Rag별 채널에서 자체적으로 재조립+완성 판단을 한다.
        var ragChunkResult = await ragServer.SendChunkAsync(
            new RagServerChunkRequest(
                chunk.SessionId, chunk.RagSelectorQuery, chunk.RequestNumber,
                chunk.FinalRequestNumber, chunk.MessageChunk, chunk.IsComplete),
            ct);

        if (!ragChunkResult.IsFinal)
        {
            return Ok(new ChunkAckResponse(ChunkReceived: true, chunk.RequestNumber));
        }

        // RagServer가 전 청크를 모아 결정+검색까지 마쳤음 — 여기서부터는 기존 파이프라인 그대로.
        var fullQuestion = assembly.Assemble();
        var messageCount = assembly.MessageCount;
        var history = assembly.History;
        chunkStore.Remove(chunk.SessionId);

        await dbServer.EnsureSessionAsync(chunk.SessionId, ct);

        var userMessageId = await dbServer.InsertMessageAsync(chunk.SessionId, "USER", fullQuestion, ct);

        await dbServer.InsertRagLogAsync(
            userMessageId, ragChunkResult.Message!, ragChunkResult.SelectRag!, TopK, ragChunkResult.RagContext!,
            ragChunkResult.RetrievalTimeMs!.Value, ct);

        // 2번째 메시지부터는 이전 대화 맥락으로 후속 질문(대명사·생략 표현)을 독립적인 질문으로 재작성해
        // LLM 답변 생성에 사용한다. RagServer 검색 자체는 원문 그대로 이미 끝난 뒤라 대상이 아니다.
        var questionForLlm = ragChunkResult.Message!;
        if (messageCount is >= 2 && history is { Count: > 0 })
        {
            var rewritten = await llmServer.RewriteQuestionAsync(history, ragChunkResult.Message!, ct);
            questionForLlm = rewritten.Rewritten;
        }

        var llmResult = await llmServer.ExecuteAsync(ragChunkResult.RagContext!, questionForLlm, ct);

        await dbServer.InsertMessageAsync(chunk.SessionId, "BOT", llmResult.Result, ct);

        return Ok(llmResult);
    }
}
