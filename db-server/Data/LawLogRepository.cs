using MySqlConnector;

namespace DbServer.Data;

public sealed class LawLogRepository(string connectionString)
{
    public async Task EnsureSessionAsync(string sessionId, string? userId, string? title, CancellationToken ct)
    {
        await using var connection = new MySqlConnection(connectionString);
        await connection.OpenAsync(ct);

        // 이미 있으면 아무 것도 바꾸지 않는 no-op upsert
        await using var command = connection.CreateCommand();
        command.CommandText = """
            INSERT INTO chat_sessions (session_id, user_id, title)
            VALUES (@session_id, @user_id, @title)
            ON DUPLICATE KEY UPDATE session_id = session_id
            """;
        command.Parameters.AddWithValue("@session_id", sessionId);
        command.Parameters.AddWithValue("@user_id", (object?)userId ?? DBNull.Value);
        command.Parameters.AddWithValue("@title", (object?)title ?? DBNull.Value);
        await command.ExecuteNonQueryAsync(ct);
    }

    public async Task<string> InsertMessageAsync(
        string sessionId, string senderType, string messageText, CancellationToken ct)
    {
        var messageId = Guid.NewGuid().ToString();

        await using var connection = new MySqlConnection(connectionString);
        await connection.OpenAsync(ct);

        await using var command = connection.CreateCommand();
        command.CommandText = """
            INSERT INTO chat_messages (message_id, session_id, sender_type, message_text)
            VALUES (@message_id, @session_id, @sender_type, @message_text)
            """;
        command.Parameters.AddWithValue("@message_id", messageId);
        command.Parameters.AddWithValue("@session_id", sessionId);
        command.Parameters.AddWithValue("@sender_type", senderType);
        command.Parameters.AddWithValue("@message_text", messageText);
        await command.ExecuteNonQueryAsync(ct);

        return messageId;
    }

    public async Task<string> InsertRagLogAsync(
        string messageId, string searchQuery, string targetIndex, int topK,
        string retrievedChunks, int? retrievalTimeMs, CancellationToken ct)
    {
        var logId = Guid.NewGuid().ToString();

        await using var connection = new MySqlConnection(connectionString);
        await connection.OpenAsync(ct);

        await using var command = connection.CreateCommand();
        command.CommandText = """
            INSERT INTO rag_retrieval_logs
                (log_id, message_id, search_query, target_index, top_k, retrieved_chunks, retrieval_time_ms)
            VALUES
                (@log_id, @message_id, @search_query, @target_index, @top_k, @retrieved_chunks, @retrieval_time_ms)
            """;
        command.Parameters.AddWithValue("@log_id", logId);
        command.Parameters.AddWithValue("@message_id", messageId);
        command.Parameters.AddWithValue("@search_query", searchQuery);
        command.Parameters.AddWithValue("@target_index", targetIndex);
        command.Parameters.AddWithValue("@top_k", topK);
        command.Parameters.AddWithValue("@retrieved_chunks", retrievedChunks);
        command.Parameters.AddWithValue("@retrieval_time_ms", (object?)retrievalTimeMs ?? DBNull.Value);
        await command.ExecuteNonQueryAsync(ct);

        return logId;
    }
}
