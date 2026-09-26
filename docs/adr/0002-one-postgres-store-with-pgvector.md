# One Postgres store with pgvector, no dedicated vector database

The first version of Fynd used a separate vector store alongside its other data, which is the
normal shape for a retrieval system. We reject that here. The Backtest is a set of relational
queries: find every Verdict produced under a given cutoff, join to the later papers, compare
against what is known now, group by Verdict class. A vector store cannot answer that, so a
relational database is required regardless, and pgvector lets the same database hold the
vector index. One store removes a second system to run and a consistency problem to manage,
and Postgres on a free tier costs nothing at this data size.
