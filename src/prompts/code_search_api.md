Generate optimized GitHub Code Search queries is challenging, please strictly follow the guidelines below to generate effective queries that can find relevant code snippets.

## Syntax Guidelines
1. Identify the key features in the code pattern or vulnerability you want to research. For example, the framework package, function names, string literals, or specific keywords.
    - You should not directly search for framework names, but you can search for the function calls.
    - If you want to search function call, use "functionName(" to search for function calls, and use "functionName" to search for both function calls and definitions.
    - You should quote the terms you are searching for.
2. Generate 3-5 diverse queries that balance specificity and breadth. Always use `language:` to avoid noise , and use operators like `AND`, `OR`, `NOT` to refine your search.
    - You should always use `language:` to specify ONE programming language.
    - You can use `AND` to combine multiple search terms, which means all terms must be present in the results.
    - You can use `OR` to search for results that contain either of the terms, but you cannot use parentheses to group OR conditions. For example, `term1 OR term2 AND term3` is valid, but `(term1 OR term2) AND term3` is not valid.
    - You can use `NOT` to exclude results that contain a specific term. For example, `term1 NOT term2` will return results that contain `term1` but do not contain `term2`.
    - You should not make queries overly complex, at most 5 operations (AND, OR NOT) are recommended.

## Valid GitHub Search Query examples:
- `"Crypto.Hash.MD5" AND language:python` --- Correct use
- `"executeQuery(" AND"SELECT * FROM" AND language:java` --- Correct use of quoted phrase and language filter, "executeQuery(" is for searching function calls (Recommended when searching for specific function invocations).
- `"useState=true" AND language:javascript` --- Correct use of quoted phrase and language filter, "useState=true" is for searching a short expression.

## Invalid GitHub Search Query examples:
- `hashlib.md5 OR "Crypto.Hash.MD5" OR sha256` --- Missing language filter
- `(hashlib.md5 OR "Crypto.Hash.MD5") AND sha256 AND language:python` --- Parentheses are NOT supported
- `(hashlib.md5 OR "Crypto.Hash.MD5") AND (sha256 OR bcrypt OR sha3_*) NOT "md5" AND language:python` --- Too complex and parentheses is NOT supported
