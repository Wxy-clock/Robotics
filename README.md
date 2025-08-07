# Robotic Arm Multimeter Testing System

An automated multimeter testing system that uses computer vision and robotic arm control to perform precision multimeter calibration and testing.

## Project Overview

This project aims to achieve automated multimeter testing through computer vision recognition and robotic arm control. The system is currently in the development and refactoring phase, with ongoing improvements to code structure, maintainability, and scalability.

## Project Goals

- **Objective**: Implement automated multimeter testing using computer vision and robotic arm automation
- **Current Status**: Under active development with code refactoring and standardization in progress  
- **Key Technologies**: Python, OpenCV (computer vision), robotic arm control libraries

## System Requirements

- Python 3.8+
- OpenCV for computer vision processing
- Robotic arm controller (specific model and control libraries required)
- Standard signal source for calibration
- Database system (MySQL)
- Recommended to use virtual environment for dependency management

## Installation and Setup

1. **Clone Repository**:
   ```bash
   git clone <repository_url>
   cd <project_directory>
   ```

2. **Create Virtual Environment** (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run Application**:
   ```bash
   python multimeter_gui.py
   ```

## Project Structure

### Main Modules
- `multimeter_gui.py` - Main GUI application and user interface logic
- `image_processing.py` - Computer vision for LCD digit and QR code recognition  
- `robot_controller.py` - Robotic arm control and coordination
- `system_config.py` - Configuration constants and system settings
- `README_REFACTORING.md` - Detailed refactoring documentation

### Key Features
- **Automated Testing**: Robotic probe insertion and measurement execution
- **Computer Vision**: LCD digit recognition and QR code scanning
- **Database Management**: Test data storage and retrieval
- **Report Generation**: Automated test result reporting
- **Equipment Management**: Multimeter mounting and positioning control

## Hardware Components

### Required Equipment
- 6-DOF robotic arm with gripper
- High-resolution camera for computer vision
- Precision standard signal source
- Pressure sensors for feedback
- Turntable for equipment positioning
- Microcontroller for hardware coordination

### Communication Interfaces
- Ethernet connection to robot controller
- Serial communication with microcontroller  
- USB camera interface
- Database server connection

## Software Architecture

### GUI Components
- **System Initializer**: Hardware communication testing and system startup
- **Multimeter Interface**: Main navigation and operation control
- **Equipment Manager**: Multimeter mounting and positioning
- **Measurement Runner**: Automated test execution
- **Report Generator**: Test result analysis and export

### Control Systems
- **Robot Controller**: High-level robot arm coordination
- **Image Processing**: Computer vision algorithms for recognition
- **Database Manager**: Data storage and retrieval operations
- **Communication Handler**: Hardware interface management

## Development Status

### Completed Features
- [x] Basic robotic arm control and computer vision integration
- [x] Code structure refactoring and naming standardization
- [x] Configuration management system
- [x] Comprehensive documentation

### In Progress
- [ ] Complete module refactoring
- [ ] Comprehensive testing framework
- [ ] Performance optimization
- [ ] Documentation completion

### Planned Features
- [ ] Advanced error handling and recovery
- [ ] Remote monitoring capabilities
- [ ] Enhanced reporting features
- [ ] Configuration management UI

## Usage Instructions

### System Startup
1. Ensure all hardware components are connected and powered
2. Run communication tests from System Initializer
3. Verify robot arm positioning and camera calibration
4. Load multimeter configuration data

### Equipment Setup
1. Use Equipment Manager to mount multimeters on turntable
2. Perform position calibration using computer vision
3. Verify probe contact positioning
4. Initialize measurement parameters

### Running Tests
1. Select test mode (automatic or manual)
2. Configure measurement parameters
3. Execute test sequence
4. Monitor progress and handle any errors
5. Generate and export test reports

## Contributing

This project is under active development. Please follow coding standards:

- Use English naming conventions (see NAMING_CONVENTION.md)
- Add comprehensive documentation for new features
- Include unit tests for new functionality
- Follow PEP 8 style guidelines

## Development Roadmap

### Phase 1: Refactoring and Stabilization
- Complete code refactoring to English naming conventions
- Implement comprehensive error handling
- Add logging and monitoring capabilities
- Create automated test suite

### Phase 2: Feature Enhancement
- Advanced measurement algorithms
- Real-time monitoring dashboard
- Remote operation capabilities
- Enhanced reporting and analytics

### Phase 3: Production Readiness
- Performance optimization
- Security enhancements
- Deployment automation
- User training materials

## Contact Information

For technical questions or collaboration inquiries, please contact the development team or submit an issue through the project repository.

## License

This project is developed for research and educational purposes. Please refer to the license file for specific terms and conditions.

---

**Note**: This project is under active development with frequent updates. Please check the documentation regularly for the latest information and best practices.

*Last updated: 2025-01-XX*