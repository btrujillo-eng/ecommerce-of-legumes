from secrets import choice


def generate_restore_code(n: int = 6) -> str:
    sequence =  "0123456789"
    return ''.join(choice(sequence) for _ in range(n))