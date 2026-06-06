local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local tokens_to_consume = tonumber(ARGV[3])
local now = tonumber(ARGV[4])

local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(bucket[1]) or capacity
local last_refill = tonumber(bucket[2]) or now

local elapsed = now - last_refill
local refilled = math.min(capacity, tokens + elapsed * refill_rate)

if refilled < tokens_to_consume then
    return {0, refilled, 0}  -- denied, remaining, retry_after
end

local new_tokens = refilled - tokens_to_consume
local retry_after = math.ceil((tokens_to_consume - refilled) / refill_rate)

redis.call('HMSET', key, 'tokens', new_tokens, 'last_refill', now)
redis.call('EXPIRE', key, 3600)

return {1, new_tokens, 0}  -- allowed, remaining, retry_after
