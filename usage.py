import tiktoken

# Token cost rates
INPUT_TOKENS_COST = 5 / 1_000_000
OUTPUT_TOKENS_COST = 20 / 1_000_000

# Initialize encoding for model
encoding = tiktoken.encoding_for_model("gpt-4o")

def estimate_tokens_and_price(text: str, token_type: str = "input"):
    """
    Estimate the number of tokens and the associated cost for a given text.

    Args:
        text (str): The text to encode.
        token_type (str): "input" or "output" to determine pricing.

    Returns:
        tuple: (num_tokens (int), price (float))

    Raises:
        RuntimeError: If encoding fails or invalid token_type.
    """
    try:
        tokens = encoding.encode(text)
        num_tokens = len(tokens)
        if token_type == "input":
            price = num_tokens * INPUT_TOKENS_COST
        elif token_type == "output":
            price = num_tokens * OUTPUT_TOKENS_COST
        else:
            raise ValueError("token_type must be 'input' or 'output'")
        return num_tokens, price
    except Exception as e:
        raise RuntimeError(f"Error estimating tokens and price: {e}")
