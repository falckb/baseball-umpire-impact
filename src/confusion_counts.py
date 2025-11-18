import duckdb
con = duckdb.connect("statcast.duckdb")
df = con.execute("""
SELECT truth_vs_type, COUNT(*) AS n
FROM pitches_qualified
WHERE truth_vs_type IS NOT NULL
GROUP BY 1
ORDER BY n DESC;
""").df()
print(df.to_string(index=False))
