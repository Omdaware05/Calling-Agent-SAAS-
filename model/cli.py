import argparse
import sys
import json
from classifier.engine import IntentClassifier


def main():
    parser = argparse.ArgumentParser(
        description="Two-Class AI Call Transcript Intent Classifier (INTERESTED vs NOT_INTERESTED)"
    )
    parser.add_argument("-t", "--transcript", type=str, help="Call transcript text")
    parser.add_argument("-f", "--file", type=str, help="Path to transcript file")
    parser.add_argument("-i", "--interactive", action="store_true", help="Start interactive classification session")
    parser.add_argument("--explain", action="store_true", help="Provide detailed diagnostic reasoning")
    parser.add_argument("--raw-json", action="store_true", help="Output strictly raw JSON")

    args = parser.parse_args()
    classifier = IntentClassifier()

    if args.interactive:
        print("\n=======================================================")
        print("  AI Call Transcript Intent Classifier Interactive CLI")
        print("  Classes: INTERESTED | NOT_INTERESTED")
        print("  Type 'exit' or 'quit' to terminate. Enter EOF (Ctrl+Z/D) to classify multi-line.")
        print("=======================================================\n")

        while True:
            try:
                print("Paste/Type transcript below (enter '---' on a new line when done):")
                lines = []
                while True:
                    line = input()
                    if line.strip() == "---" or line.strip().lower() in ["exit", "quit"]:
                        break
                    lines.append(line)

                if line.strip().lower() in ["exit", "quit"]:
                    break

                text = "\n".join(lines).strip()
                if not text:
                    continue

                if args.explain:
                    res = classifier.classify_detailed(text)
                    print("\n--- Detailed Diagnostic ---")
                    print(f"Classification: {res.classification.value}")
                    print(f"Confidence:     {res.confidence * 100:.1f}%")
                    print(f"Rule Applied:   {res.rule_applied}")
                    print(f"Reason:         {res.reason}")
                    print(f"Signals:        {', '.join(res.signals_detected) if res.signals_detected else 'None'}")
                    print(f"Languages:      {', '.join(res.languages_detected)}")
                    print("----------------------------\n")
                else:
                    res = classifier.classify_strict(text)
                    print(f"\nResult: {json.dumps(res, indent=2)}\n")

            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                break
        return

    text = None
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            print(f"Error reading file {args.file}: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.transcript:
        text = args.transcript
    elif not sys.stdin.isatty():
        text = sys.stdin.read()

    if not text:
        parser.print_help()
        sys.exit(1)

    if args.explain:
        res = classifier.classify_detailed(text)
        print(json.dumps(res.model_dump(), indent=2, ensure_ascii=False))
    else:
        res = classifier.classify_strict(text)
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
