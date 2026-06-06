local key = KEYS[1]
local window_seconds = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local request_id = ARGV[4]

local window_start = now - window_seconds

redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)
local count = redis.call('ZCARD', key)

if count >= limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_after = 0
    if #oldest >= 2 then
        retry_after = math.ceil(tonumber(oldest[2]) + window_seconds - now)
    else
        retry_after = window_seconds
    end
    return {0, count, retry_after}
end

redis.call('ZADD', key, now, request_id)
redis.call('EXPIRE', key, window_seconds + 10)

return {1, limit - count - 1, 0}
