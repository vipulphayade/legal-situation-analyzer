# Migration Steps

1. Back up the existing v13 database and dataset.
2. Replace the dataset JSON with the new full dataset.
3. Run the updated import service.
4. Rebuild embeddings.
5. Restart the API.
6. Validate these queries:
   - notice period for conducting managing committee meeting
   - quorum for committee meeting
   - transfer notice before committee meeting
   - AGM notice period
