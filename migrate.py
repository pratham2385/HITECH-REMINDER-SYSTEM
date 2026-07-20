import os
from src.db.session import init_database
from src.db.models import *

def run():
    print("Creating missing tables...")
    init_database()
    print("Done.")

if __name__ == "__main__":
    run()
