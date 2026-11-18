	
Response body
Download
[
  {
    "id": 2,
    "post_id": 1,
    "platform": "linkedin",
    "text": "Why retries need idempotency\n\nA retry after a timeout must not create a second post.\n\nThis is the heart of reliable publishing.\n\nWhat is your experience with this?\n\n#retries #idempotency",
    "status": "draft",
    "created_at": "2026-11-18 15:04:40"
  },
  {
    "id": 3,
    "post_id": 1,
    "platform": "telegram",
    "text": "New post: Why retries need idempotency\n\nA retry after a timeout must not create a second post.\n\n#retries #idempotency",
    "status": "draft",
    "created_at": "2026-11-18 15:04:40"
  },
  {
    "id": 1,
    "post_id": 1,
    "platform": "x",
    "text": "Why retries need idempotency. A retry after a timeout must not create a second post. #retries #idempotency",
    "status": "draft",
    "created_at": "2026-11-18 15:04:40"
  }
]
Response headers
 content-length: 730 
 content-type: application/json 
 date: Wed,18 Nov 2026 15:04:39 GMT 
 server: uvicorn 



 again 

Code	Details
409
Undocumented
Error: Conflict

Response body
Download
{
  "detail": "Variants were already generated for this post."
}
Response headers
 content-length: 59 
 content-type: application/json 
 date: Wed,18 Nov 2026 15:19:07 GMT 
 server: uvicorn 


 Curl

curl -X 'GET' \
  'http://127.0.0.1:8000/posts/1' \
  -H 'accept: */*'
Request URL
http://127.0.0.1:8000/posts/1
Server response
Code	Details
200	
Response body
Download
{
  "id": 1,
  "source_type": "markdown",
  "source_url": null,
  "title": "Why retries need idempotency",
  "body": "# Why retries need idempotency\n\nA retry after a timeout must not create a second post. This is the heart of reliable publishing.",
  "created_at": "2026-11-18 14:59:58"
}
Response headers
 content-length: 265 
 content-type: application/json 
 date: Wed,18 Nov 2026 15:19:49 GMT 
 server: uvicorn 






 Responses
Curl

curl -X 'PUT' \
  'http://127.0.0.1:8000/variants/1' \
  -H 'accept: */*' \
  -H 'Content-Type: application/json' \
  -d '{
  "text": "string"
}'
Request URL
http://127.0.0.1:8000/variants/1
Server response
Code	Details
200	
Response body
Download
{
  "id": 1,
  "post_id": 1,
  "platform": "x",
  "text": "string",
  "status": "draft",
  "created_at": "2026-11-18 15:04:40"
}
Response headers
 content-length: 103 
 content-type: application/json 
 date: Wed,18 Nov 2026 15:22:52 GMT 
 server: uvicorn 