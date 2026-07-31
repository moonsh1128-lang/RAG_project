using System.Collections.Concurrent;
using MainServer.Models;

namespace MainServer.Services;

public sealed class ChunkAssembly
{
    private readonly ConcurrentDictionary<int, string> _chunks = new();
    private int? _finalRequestNumber;

    // 1번 청크에만 실리지만, 실제로 쓰는 시점(마지막 청크)까지 들고 있어야 해서 여기 보관.
    public int? MessageCount { get; private set; }
    public List<HistoryTurn>? History { get; private set; }

    public void Add(
        int requestNumber, string messageChunk, int? finalRequestNumber,
        int? messageCount = null, List<HistoryTurn>? history = null)
    {
        _chunks[requestNumber] = messageChunk;
        if (finalRequestNumber is not null)
        {
            _finalRequestNumber = finalRequestNumber;
        }
        if (messageCount is not null)
        {
            MessageCount = messageCount;
            History = history;
        }
    }

    public bool IsReady(bool isComplete)
    {
        if (!isComplete || _finalRequestNumber is null)
        {
            return false;
        }

        for (var i = 1; i <= _finalRequestNumber; i++)
        {
            if (!_chunks.ContainsKey(i))
            {
                return false;
            }
        }
        return true;
    }

    public string Assemble()
    {
        return string.Concat(Enumerable.Range(1, _finalRequestNumber!.Value).Select(i => _chunks[i]));
    }
}

// session_id별로 진행 중인 청크 조립을 저장해 두는 곳 (MainServer 자신의 DB 저장용 재조립)
public sealed class ChunkAssemblyStore
{
    private readonly ConcurrentDictionary<string, ChunkAssembly> _bySession = new();

    public ChunkAssembly GetOrAdd(string sessionId) => _bySession.GetOrAdd(sessionId, _ => new ChunkAssembly());

    public void Remove(string sessionId) => _bySession.TryRemove(sessionId, out _);
}
