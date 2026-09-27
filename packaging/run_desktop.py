import multiprocessing

from backend.desktop.app import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
