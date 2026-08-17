"""Compatibility entry point; use calculate_scale.py for new analyses."""

from calculate_scale import main


if __name__ == "__main__":
    print("AVERTISSEMENT: test_scale.py est obsolete; execution de calculate_scale.py.")
    raise SystemExit(main())
