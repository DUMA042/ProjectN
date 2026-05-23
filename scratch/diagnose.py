import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import traceback
from owl.nominal.processor import NominalProcessor

def main():
    file_path = Path("nest/Nominal_Folder/AHRD_Nominal_202605_v1.xlsx")
    processor = NominalProcessor(file_path)
    try:
        processor.process()
    except Exception as e:
        print("\n\n==== FATAL ERROR CAUGHT ====")
        print(f"Exception: {type(e).__name__}: {e}")
        if hasattr(e, "__cause__") and e.__cause__:
            print(f"Cause: {type(e.__cause__).__name__}: {e.__cause__}")
        print("\nTraceback:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
