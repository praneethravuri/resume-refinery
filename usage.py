import tiktoken

INPUT_TOKENS_COST = 5 / 1_000_000
OUTPUT_TOKENS_COST = 20 / 1_000_000

encoding = tiktoken.encoding_for_model("gpt-4o")

def estimate_tokens_and_price(text: str, type: str = "input"):
    tokens = encoding.encode(text)
    num_tokens = len(tokens)
    if type == "input":
        price = num_tokens * INPUT_TOKENS_COST
    elif type == "output":
        price = num_tokens * OUTPUT_TOKENS_COST
    else:
        raise ValueError("type must be 'input' or 'output'")
    print(f"Number of tokens: {num_tokens}")
    print(f"Estimated price: ${price:.6f}")
    return num_tokens, price