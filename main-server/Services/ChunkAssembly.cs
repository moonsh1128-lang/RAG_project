using System.Collections.Concurrent;

namespace MainServer.Services;

public sealed class ChunkAssembly
{
    private readonly ConcurrentDictionary<int, string> _chunks = new();
    private int? _finalRequestNumber;

    public void Add(int requestNumber, string messageChunk, int? finalRequestNumber)
    {
        _chunks[requestNumber] = messageChunk;
        if (finalRequestNumber is not null)
        {
            _finalRequestNumber = finalRequestNumber;
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
