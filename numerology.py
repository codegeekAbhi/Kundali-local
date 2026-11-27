"""Date-only numerology using a documented single-digit reduction."""

import argparse
from datetime import date


def reduce_number(number):
    while number >= 10:
        number = sum(map(int, str(number)))
    return number


def date_numbers(birth, year):
    return {
        "Life Path": reduce_number(birth.year + birth.month + birth.day),
        "Birth Day": reduce_number(birth.day),
        "Personal Year": reduce_number(year + birth.month + birth.day),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("birth_date", type=date.fromisoformat)
    parser.add_argument("--year", type=int, default=date.today().year)
    args = parser.parse_args()
    if not 1 <= args.year <= 9999:
        parser.error("--year must be between 1 and 9999.")
    for label, number in date_numbers(args.birth_date, args.year).items():
        print(f"{label}: {number}")


if __name__ == "__main__":
    main()
