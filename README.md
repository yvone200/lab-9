NJAMBI YVONE : C027-01-0842/2024 
Exercise 1: Document Search with Filters
​How to make search efficient with many documents?  
​Add database B-Tree or GIN indexes to heavily searched columns (city, status, original_filename).  
​Implement query pagination using limit and offset parameters to restrict large database payloads.  
​Should managers see all documents while staff see only their own?  
​Yes. Staff users are scoped strictly to records where uploader_id == current_user.id, whereas manager and admin roles have global access.  
​Exercise 2: Document Versioning
​How to track changes between versions?  
​Store a version counter integer (version: int) on the Document model and append unique timestamps to filenames (v1_..., v2_...) on server disk storage.  
​Should you store old versions or delete them?  
​Retain old physical files and database rows for auditing, legal compliance, and rollbacks.  
​Exercise 3: Webhook Notifications
​How to handle retries if a webhook fails?  
​Use an asynchronous task queue (e.g., Celery / Redis) with exponential backoff (retrying delivery after 1s, 5s, 30s).  
​What security measures to implement?  
​Enforce HTTPS for webhook URLs.  
​Sign outgoing webhook payloads using a shared secret and HMAC (X-Hub-Signature) so recipients can verify authenticity.
