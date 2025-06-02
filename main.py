import sys
import os
from PyQt5.QtWidgets import QApplication

# Configuration du path pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from logger import CSILogger
from core.pipeline import CSIPipeline
from gui.main_window import MainWindow

def initialize_application():
    """Initialise et configure l'application"""
    # Setup logger
    logger = CSILogger()
    logger.log("Initializing application...", level='info')
    
    try:
        # Create pipeline
        pipeline = CSIPipeline(logger=logger)
        
        # Create and show main window
        app = QApplication(sys.argv)
        window = MainWindow(pipeline, logger=logger)
        window.show()
        
        logger.log("Application started successfully", level='info')
        
        return app, window
    except Exception as e:
        logger.log(f"Application initialization failed: {str(e)}", level='critical')
        raise

def main():
    try:
        app, window = initialize_application()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()