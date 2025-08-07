# Project Structure After Refactoring

## Overview
This document provides a comprehensive overview of the refactored project structure, showing the transformation from Chinese/pinyin naming to English naming conventions.

## Directory Structure

```
Robotics/
©À©¤©¤ README.md                           # Main project documentation (updated)
©À©¤©¤ README_REFACTORING.md              # Refactoring details and migration guide
©À©¤©¤ NAMING_CONVENTION.md               # Naming conventions specification
©À©¤©¤ requirements.txt                   # Python dependencies
©À©¤©¤ 
©À©¤©¤ # Refactored Core Modules
©À©¤©¤ multimeter_gui.py                  # Main GUI application (was: wyb_gui.py)
©À©¤©¤ image_processing.py                # Computer vision module (was: ewm_and_lcd_formal.py)
©À©¤©¤ robot_controller.py                # Robot control module (was: robot_act_new.py)
©À©¤©¤ system_config.py                   # Configuration constants (new)
©À©¤©¤ 
©À©¤©¤ # Original Files (to be refactored)
©À©¤©¤ wyb_gui.py                         # Original GUI file (Chinese naming)
©À©¤©¤ ewm_and_lcd_formal.py             # Original image processing
©À©¤©¤ robot_act_new.py                   # Original robot controller
©À©¤©¤ MvErrorDefine_const.py             # Camera error definitions
©À©¤©¤ 
©À©¤©¤ # Documentation Files
©À©¤©¤ README_2.md                        # SDK documentation
©¸©¤©¤ [other files...]
```

## File Mapping and Transformations

### Main Application Files

| Original File | Refactored File | Purpose |
|---------------|-----------------|---------|
| `wyb_gui.py` | `multimeter_gui.py` | Main GUI application with all interfaces |
| `ewm_and_lcd_formal.py` | `image_processing.py` | Computer vision and image processing |
| `robot_act_new.py` | `robot_controller.py` | Robot arm control and coordination |
| N/A | `system_config.py` | Centralized configuration management |

### Class Name Transformations

| Original Class | Refactored Class | Responsibility |
|----------------|------------------|----------------|
| `system_wyb` | `SystemInitializer` | System startup and communication testing |
| `wyb` | `MultimeterInterface` | Main multimeter testing interface |
| `equip` | `EquipmentManager` | Equipment mounting/unmounting |
| `run` | `MeasurementRunner` | Automated measurement execution |
| `run_manual` | `ManualMeasurementRunner` | Manual measurement operations |
| `rotate_zp_ai` | `TurntableController` | Turntable rotation control |
| `wyb_new` | `NewMultimeterRegistration` | New multimeter model registration |
| `report` | `ReportGenerator` | Test result reporting |
| `renew_wyb` | `DataManager` | Data import/export management |
| `find_way` | `DataQueryInterface` | Database query interface |
| `find_result` | `QueryResultDisplay` | Query result display and export |

### Function Name Transformations

#### GUI Functions
| Original Function | Refactored Function | Purpose |
|-------------------|-------------------|---------|
| `wyb_equip()` | `_open_equipment_manager()` | Open equipment interface |
| `wyb_start()` | `_start_measurement()` | Start automatic measurement |
| `wyb_manual()` | `_start_manual_measurement()` | Start manual measurement |
| `wyb_exit()` | `_return_to_system_initializer()` | Return to main menu |
| `system_test()` | `_test_system_communication()` | Test hardware communication |

#### Image Processing Functions
| Original Function | Refactored Function | Purpose |
|-------------------|-------------------|---------|
| `shuzishibie()` | `recognize_digits_neural_network()` | Neural network digit recognition |
| `danzishibie()` | `recognize_single_digit()` | Single digit pattern recognition |
| `LCD_dingwei()` | `detect_lcd_screen()` | LCD screen detection and extraction |
| `shibie()` | `process_recognition_results()` | Process multiple recognition results |

#### Robot Control Functions
| Original Function | Refactored Function | Purpose |
|-------------------|-------------------|---------|
| `movej_PTP_getJ()` | `move_to_joint_position()` | Move robot to joint position |
| `movej_PTP_getP()` | `move_to_cartesian_position()` | Move robot to Cartesian position |
| `movel_PTP()` | `move_linear()` | Linear robot movement |
| `send_io()` | `send_gripper_command()` | Control gripper open/close |
| `send_givepress()` | `read_pressure_value()` | Read pressure sensor |
| `jiajv()` | `insert_probe()` | Insert testing probe |
| `jiajv_back()` | `remove_probe()` | Remove testing probe |

### Variable Name Transformations

#### Global Variables
| Original Variable | Refactored Variable | Purpose |
|-------------------|-------------------|---------|
| `addr_ui` | `UI_BASE_PATH` | UI files base directory |
| `hang` | `CURRENT_ROW` | Current table row |
| `vector_wyb` | `measurement_vector` | Measurement data vector |
| `wyb_num_all` | `multimeter_models` | List of multimeter models |
| `wyb_style_all` | `multimeter_types` | List of multimeter types |
| `equip_image` | `equipment_image_path` | Equipment image file path |
| `db` | `database_connection` | Database connection object |
| `tool_x`, `tool_y` | `tool_coordinate_x`, `tool_coordinate_y` | Tool coordinates |
| `buchang_x`, `buchang_y` | `position_offset_x`, `position_offset_y` | Position offsets |
| `photo_num` | `photo_counter` | Photo counter |

#### Measurement Variables
| Original Variable | Refactored Variable | Purpose |
|-------------------|-------------------|---------|
| `vector_v1`, `vector_v2` | `voltage_vector_1`, `voltage_vector_2` | Voltage measurement vectors |
| `bzy_v1`, `bzy_v2` | `standard_voltage_1`, `standard_voltage_2` | Standard voltage values |
| `vector_a1-a4` | `current_vector_1-4` | Current measurement vectors |
| `bzy_a1-a4` | `standard_current_1-4` | Standard current values |

## Configuration Management

### New Configuration Structure

The new `system_config.py` provides centralized configuration with these categories:

1. **Application Information**
   - Version, author, application name
   
2. **File Paths and Directories**
   - UI files, image directories, model paths
   - Export/import default locations
   
3. **Database Configuration**
   - Connection parameters, table names
   
4. **Hardware Configuration**
   - Serial ports, robot IP, coordinate systems
   - Pressure thresholds, timing constants
   
5. **Measurement Configuration**
   - Limits, ranges, vector sizes
   - Accuracy thresholds
   
6. **Error Codes and Messages**
   - Standardized error handling
   
7. **Communication Protocols**
   - Serial command definitions

### Benefits of New Structure

1. **Maintainability**: Clear separation of concerns
2. **Readability**: English naming throughout
3. **Documentation**: Comprehensive docstrings and comments
4. **Type Safety**: Type hints for better IDE support
5. **Error Handling**: Consistent error patterns
6. **Configuration**: Centralized settings management
7. **Testing**: Modular structure enables unit testing
8. **Scalability**: Easy to extend with new features

## Migration Path

### For Existing Code
1. Update import statements to use new module names
2. Replace class instantiations with new class names  
3. Update method calls to use new function names
4. Replace hardcoded values with configuration constants
5. Update variable references to use new naming

### For New Development
1. Follow naming conventions in NAMING_CONVENTION.md
2. Use configuration constants from system_config.py
3. Add comprehensive docstrings and type hints
4. Implement proper error handling patterns
5. Write unit tests for new functionality

## Documentation Standards

### Code Documentation
- Comprehensive module-level docstrings
- Class and method documentation with parameters and return values
- Type hints for all function signatures
- Inline comments for complex logic

### File Headers
Every Python file includes:
- Encoding specification
- Module description
- Class/function listings
- Dependencies documentation
- Usage examples where appropriate

### Naming Conventions
- Classes: PascalCase (e.g., `MultimeterInterface`)
- Functions/Methods: snake_case (e.g., `start_measurement`)
- Variables: snake_case (e.g., `measurement_data`)
- Constants: ALL_CAPS_WITH_UNDERSCORES (e.g., `MAX_PRESSURE`)
- Private methods: Leading underscore (e.g., `_internal_method`)

This refactoring provides a solid foundation for future development while maintaining backward compatibility during the transition period.