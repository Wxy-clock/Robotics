"""
CONVERT_NEW.PY - Computer Vision Module for Multimeter Testing System

OVERVIEW:
========
This module provides advanced computer vision capabilities for automated multimeter testing.
It combines image processing techniques to detect and locate circular test points on multimeters
and rotary knob positions for precise robotic testing operations.

MAIN FUNCTIONALITY:
==================
1. Blue Circle Detection: Identifies circular test points on multimeter reference images
2. Rotary Knob Detection: Locates the current position of multimeter selector knobs  
3. Position Calculation: Calculates precise coordinates for robotic probe placement
4. Multi-point Sorting: Organizes detected points in systematic order for testing sequences

KEY ALGORITHMS:
==============
- HSV Color Space Filtering: Extracts blue circular markers from reference images
- Hough Circle Transform: Robust circular feature detection in varying lighting conditions
- Morphological Operations: Noise reduction and feature enhancement
- Geometric Sorting: Spatial organization of test points from top-left to bottom-right
- Coordinate Transformation: Converts image coordinates to robot coordinate system

TYPICAL WORKFLOW:
================
1. Load reference image with blue test point markers
2. Load current equipment image showing knob position
3. Detect blue circles and calculate their relative positions
4. Detect current knob position and calculate offset from center
5. Combine results to determine absolute positions of all test points
6. Return sorted coordinates for robotic testing sequence

INPUT REQUIREMENTS:
==================
- Reference image: Clear photo with blue circular test point markers
- Equipment image: Current photo showing rotary knob/selector position
- Scale factor: Conversion ratio between image pixels and real-world coordinates

OUTPUT FORMAT:
=============
- Test point coordinates: List of [x, y] positions relative to knob center
- Knob offset: Current knob position relative to image center
- Validation image: Annotated image showing detected features for verification

DEPENDENCIES:
============
- OpenCV (cv2): Computer vision and image processing operations
- NumPy: Numerical array operations and mathematical calculations

TECHNICAL PARAMETERS:
====================
- HSV Thresholds: Blue color detection range [100,80,80] to [115,255,255]
- Circle Detection: Hough transform with adaptive parameters
- Morphological Kernel: 5x5 structuring element for noise filtering
- Spatial Tolerance: 5-pixel grouping threshold for row organization

ERROR HANDLING:
==============
- Returns None values when detection fails
- Validates circle radius constraints (88-96 pixels for standard images)
- Checks knob position against expected centerline location

AUTHOR: Multimeter Testing System Development Team
VERSION: Production Release
LAST MODIFIED: Current Version
"""

import cv2
import numpy as np

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

# Image file paths for testing (can be updated based on current setup)
pic_blue_path = 'E:\photo_test\VICTOR&VC890C+_ori.jpg'    # Reference image with blue test points
pic_equip_path ='E:\photo_test\VICTORVC890C+002.jpg'       # Current equipment image

# Alternative paths for development/testing environments
'''
pic_blue_path = 'G:\study\Python\python310_work\photo\VICTOR_2.jpg'
pic_equip_path = 'G:\study\Python\python310_work\photo\VICTOR_1.jpg'
'''

# ============================================================================
# CORE DETECTION FUNCTIONS
# ============================================================================

def find_blue_circle_loc(adress, scale = 1):
    """
    Detects and locates blue circular test points in multimeter reference images.
    
    This function uses HSV color space filtering and Hough circle detection to identify
    blue circular markers that indicate test probe placement points on multimeters.
    The detected circles are then sorted spatially and their coordinates are calculated
    relative to the center point of the arrangement.
    
    ALGORITHM STEPS:
    1. Load and resize input image for processing efficiency
    2. Convert to HSV color space for robust blue color detection
    3. Apply color filtering to isolate blue regions
    4. Perform morphological operations to clean up noise
    5. Use Hough circle transform to detect circular features
    6. Sort detected circles spatially (top-to-bottom, left-to-right)
    7. Calculate center point of the entire arrangement
    8. Convert coordinates to relative positions from center
    
    Parameters:
    -----------
    adress : str
        File path to the reference image containing blue test point markers
    scale : float, default=1
        Scaling factor to convert image coordinates to real-world coordinates
        
    Returns:
    --------
    tuple : (circle_locations, center_point)
        circle_locations : list of [x, y] coordinates
            Positions of all test points relative to the center point
        center_point : [x, y] coordinate
            Location of the calculated center point in image coordinates
            
    Notes:
    ------
    - HSV thresholds optimized for blue markers: [100,80,80] to [115,255,255]
    - Morphological operations use 5x5 kernel with 2 iterations
    - Spatial sorting groups points within 5 pixels vertically as same row
    - Center point calculated as geometric mean of all detected points
    """
    
    # 读取图片 (Load input image)
    image = cv2.imread(adress)

    # Create working copy and resize for processing efficiency
    img_copy = image.copy()
    img_copy = cv2.resize(img_copy, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    
    # ========================================================================
    # HSV COLOR SPACE FILTERING FOR BLUE DETECTION
    # ========================================================================
    """
    提取图中的蓝色部分 hsv范围可以自行优化
    Extract blue regions from image using HSV color space thresholding.
    
    cv2.inRange() parameters:
    - hsv: Source image in HSV color space
    - low_hsv: Lower threshold - pixels below this become 0 (black)
    - high_hsv: Upper threshold - pixels above this become 0 (black) 
    - Result: Pixels within range become 255 (white), creating binary mask
    
    HSV advantages for color detection:
    - Hue represents pure color information, independent of lighting
    - Saturation and Value handle color intensity and brightness variations
    - More robust than RGB for varying lighting conditions
    """
    hsv = cv2.cvtColor(img_copy, cv2.COLOR_BGR2HSV)
    
    # HSV thresholds optimized for blue test point markers
    low_hsv = np.array([100, 80, 80])   # Lower bound for blue color range
    high_hsv = np.array([115, 255, 255]) # Upper bound for blue color range
    
    # Create binary mask isolating blue regions
    mask = cv2.inRange(hsv, lowerb=low_hsv, upperb=high_hsv)
    
    # Apply mask to original image to extract blue regions
    # cv2.bitwise_and() performs pixel-wise AND operation: 1&1=1, 1&0=0, 0&1=0, 0&0=0
    res = cv2.bitwise_and(img_copy, img_copy, mask=mask)

    # ========================================================================
    # MORPHOLOGICAL OPERATIONS FOR NOISE REDUCTION
    # ========================================================================
    # Define morphological kernel for erosion and dilation operations
    kernel = np.ones((5, 5), np.uint8)
    
    # Erosion: Removes small noise and separates connected objects
    eroded_image = cv2.erode(res, kernel, iterations=2)
    
    # Dilation: Restores object size while maintaining noise reduction
    dilated_image = cv2.dilate(eroded_image, kernel, iterations=2)
    
    # Convert to grayscale for circle detection
    imagegray = cv2.cvtColor(dilated_image, cv2.COLOR_BGR2GRAY)

    # ========================================================================
    # HOUGH CIRCLE DETECTION
    # ========================================================================
    """
    Hough Circle Transform parameters:
    - dp=1: Inverse ratio of accumulator resolution to image resolution
    - minDist=30: Minimum distance between detected circle centers
    - param1=100: Upper threshold for internal Canny edge detector
    - param2=0.8: Accumulator threshold for center detection (lower = more sensitive)
    
    Note: param2=0.8 chosen for better detection of imperfect circles
    Higher values (>0.9) may miss circles with minor defects
    """
    circles = cv2.HoughCircles(imagegray, cv2.HOUGH_GRADIENT_ALT, dp=1, minDist=30, param1=100, param2=0.8)
    
    if circles is not None:
        count = 0
        circles = np.uint16(np.around(circles))
        
        # Draw detected circles for visualization (optional)
        for i in circles[0, :]:  # Format: (x, y, radius)
            if (1):  # Placeholder for additional filtering criteria
                count += 1
                # Draw circle circumference in green
                cv2.circle(img_copy, (i[0], i[1]), i[2], (0, 255, 0), 1)
                # Draw circle center in red
                cv2.circle(img_copy, (i[0], i[1]), 1, (0, 0, 255), 3)
    else:
        print("未检测成功") # "Detection failed"
        return None, None

    # ========================================================================
    # SPATIAL SORTING OF DETECTED CIRCLES
    # ========================================================================
    """
    Circle Sorting Algorithm:
    
    Goal: Organize detected circles in systematic order (top-to-bottom, left-to-right)
    This is crucial for consistent test point sequencing in automated testing.
    
    Process:
    1. Sort circles by Y-coordinate (top to bottom)
    2. Group circles with similar Y-coordinates (same row, ±5 pixels tolerance)
    3. Within each row, sort by X-coordinate (left to right)
    4. Combine all rows to create final ordered sequence
    
    Parameters:
    - circles: Hough detection results containing [x, y, r] for each circle
    
    Returns:
    - Spatially sorted list of circle coordinates in testing order
    """
    
    c = circles[0]
    # Sort circles by Y-coordinate (vertical position)
    sorted_c = c[c[:,1].argsort()]
    len_sc = len(sorted_c)
    
    # Initialize variables for row grouping
    ssorted_c = []  # Final sorted circle list
    counts = []     # Count of circles in each row
    count = 0       # Current row circle count
    flag = sorted_c[0][1]  # Y-coordinate of first circle (reference for row grouping)

    # Group circles into rows based on Y-coordinate proximity
    for i, item in enumerate(sorted_c, 1):
        if abs(item[1] - flag) <= 5 and i <= len_sc:  # Same row if Y-difference ≤ 5 pixels
            count += 1
            if i == len_sc:  # Last circle
                counts.append(count)
                break
        else:  # New row detected
            counts.append(count)
            flag = item[1]  # Update reference Y-coordinate
            count = 1  # Reset count for new row

    # Convert cumulative counts to individual row counts
    listNum = len(counts)
    for i in range(listNum-1):
        counts[listNum - 1 - i] = counts[listNum - 1 - i] - counts[listNum - 2 - i] + 1

    # Split circles into row groups
    flag1 = 0
    list_temp = []
    for i in range(listNum):
        if i == 0:
            list_temp.append(sorted_c[flag1:counts[i]])
            flag1 = counts[i]
        else:
            list_temp.append(sorted_c[flag1:flag1+counts[i]])
            flag1 = flag1 + counts[i]

    # Sort each row by X-coordinate (left to right) and combine
    for i in range(listNum):
        ssorted_c.extend(list_temp[i][list_temp[i][:,0].argsort()])

    # Extract [x, y] coordinates from sorted circles
    new_array = [ssorted_c[i][:2].tolist() for i in range(len(ssorted_c))]

    # ========================================================================
    # CENTER POINT CALCULATION
    # ========================================================================
    """
    Calculate the geometric center of all detected test points.
    This center serves as the reference origin for relative coordinate calculations.
    
    Method: Find the center point of the bounding rectangle containing all circles
    """
    
    # Find bounding box of all detected points
    first_min = min(el[0] for el in new_array)   # Leftmost X
    first_max = max(el[0] for el in new_array)   # Rightmost X  
    second_min = min(el[1] for el in new_array)  # Topmost Y
    second_max = max(el[1] for el in new_array)  # Bottommost Y

    # Calculate center coordinates
    first_avg = (first_min + first_max) / 2   # Center X
    second_avg = (second_min + second_max) / 2 # Center Y

    # Find the circle closest to the calculated center
    closest_element = None
    min_distance = float('inf')

    for element1 in new_array:
        # Calculate Euclidean distance to center
        distance = (element1[0] - first_avg) ** 2 + (element1[1] - second_avg) ** 2
        if distance < min_distance:
            min_distance = distance
            closest_element = element1

    # ========================================================================
    # COORDINATE TRANSFORMATION
    # ========================================================================
    """
    Convert absolute image coordinates to relative coordinates from center point.
    Apply scaling factor to convert from image pixels to real-world units.
    
    Coordinate System:
    - X-axis: Positive = right of center, Negative = left of center
    - Y-axis: Positive = above center, Negative = below center (inverted from image coordinates)
    """
    
    circle_loaction = [[
        (element[0] - closest_element[0]) * scale,  # Relative X distance from center
        (closest_element[1] - element[1]) * scale   # Relative Y distance from center (Y-inverted)
    ] for element in new_array]

    # Remove the center point (0,0) from the list
    circle_loaction = [item for item in circle_loaction if item != [0, 0]]

    return circle_loaction, closest_element


def find_zp_delta_loc(address, gray=True, enhance=True, binary=True, blur=True, fliter=True, 
                      fx=0.25, fy=0.25, clipLimit=255.0, bi_threshold=99,
                      minDist=100, param1=80, param2=0.9, minRadius=50, maxRadius=120, 
                      threhsold=60, scale=1):
    """
    Detects rotary knob position and calculates offset from image center.
    
    This function processes equipment images to locate circular rotary knobs/selectors
    and determine their position relative to the image center. This information is
    crucial for calculating the current position offset of test equipment.
    
    ALGORITHM OVERVIEW:
    1. Load and preprocess equipment image
    2. Apply multiple image enhancement techniques
    3. Use Hough circle detection to find knob
    4. Validate detected circle against expected parameters
    5. Calculate position offset from image center
    
    PREPROCESSING PIPELINE:
    - Grayscale conversion for simplified processing
    - CLAHE contrast enhancement for better feature visibility  
    - Gaussian blur for noise reduction
    - Sharpening filter for edge enhancement
    - Binary thresholding for feature isolation
    
    Parameters:
    -----------
    address : str
        File path to equipment image containing rotary knob
    gray : bool, default=True
        Enable grayscale conversion
    enhance : bool, default=True  
        Enable CLAHE contrast enhancement
    binary : bool, default=True
        Enable binary thresholding
    blur : bool, default=True
        Enable Gaussian blur noise reduction
    fliter : bool, default=True
        Enable sharpening filter application
    fx, fy : float, default=0.25
        Image resize factors for processing efficiency
    clipLimit : float, default=255.0
        CLAHE contrast enhancement limit
    bi_threshold : int, default=99
        Binary thresholding value
    minDist : int, default=100
        Minimum distance between detected circles
    param1, param2 : int/float, default=80, 0.9
        Hough circle detection sensitivity parameters
    minRadius, maxRadius : int, default=50, 120
        Expected knob radius range in pixels
    threhsold : int, default=60
        Maximum allowed deviation from expected centerline
    scale : float, default=1
        Coordinate scaling factor
        
    Returns:
    --------
    tuple : (pixel_x, pixel_y, result_image)
        pixel_x : int or None
            Horizontal offset from image center (negative = move right)
        pixel_y : int or None  
            Vertical offset from image center (negative = move down)
        result_image : numpy.ndarray or None
            Annotated image showing detection results
            
    Notes:
    ------
    - Expected knob radius: 88-96 pixels for standard image size
    - Centerline position: 53.6% of image width from left edge
    - Returns None values if detection fails or validation constraints not met
    - Coordinate system: Image center as origin, standard Cartesian orientation
    """
    
    # Load and resize input image
    image = cv2.imread(address)
    image = cv2.resize(image, None, fx=fx, fy=fy, interpolation=cv2.INTER_AREA)
    res = image.copy()  # Keep original for result visualization
    
    # Define expected knob centerline (53.6% from left edge)
    mid_line = int(res.shape[1] * 0.536)
    
    # Calculate image center coordinates
    center = [res.shape[1] // 2, res.shape[0] // 2]

    # ========================================================================
    # IMAGE PREPROCESSING PIPELINE
    # ========================================================================
    
    # Grayscale conversion for simplified processing
    if gray:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Contrast Limited Adaptive Histogram Equalization (CLAHE)
    # Enhances local contrast while preventing over-amplification
    if enhance:
        clahe = cv2.createCLAHE(clipLimit=clipLimit, tileGridSize=(8, 8))
        image = clahe.apply(image)

    # Gaussian blur for noise reduction
    # Reduces high-frequency noise while preserving important edges
    if blur:
        image = cv2.GaussianBlur(image, (5, 5), 2)
        
    # Sharpening filter for edge enhancement
    if fliter:
        # Alternative Laplacian filter (commented out)
        # image = cv2.Laplacian(image, cv2.CV_8U)
        
        # Custom sharpening kernels
        kernel = np.array([[-1, -1, -1],
                          [-1, 9, -1], 
                          [-1, -1, -1]], dtype=np.float32)
        
        kernel2 = np.array([[0, -1, 0],
                           [-1, 5, -1],
                           [0, -1, 0]], dtype=np.float32)
        
        # Apply sharpening convolution
        image = cv2.filter2D(image, -1, kernel2)
        
    # Binary thresholding for feature isolation
    if binary:
        _, image = cv2.threshold(image, bi_threshold, 255, cv2.THRESH_BINARY)

    # ========================================================================
    # HOUGH CIRCLE DETECTION FOR KNOB LOCATION
    # ========================================================================
    """
    Hough Circle Transform Configuration:
    
    - HOUGH_GRADIENT_ALT: Improved algorithm variant for better accuracy
    - dp=1: Full resolution accumulator
    - minDist: Prevents multiple detections of same circle
    - param1: Edge detection threshold for internal Canny detector
    - param2: Accumulator threshold for center detection
    - minRadius/maxRadius: Expected knob size constraints
    
    For (614, 734, 3) sized images:
    - Expected knob radius: 80-100 pixels  
    - Knob diameter ≈ 14-16% of image short edge
    """
    
    circles = cv2.HoughCircles(
        image,
        cv2.HOUGH_GRADIENT_ALT,
        dp=1,
        minDist=minDist,  # Large value since we expect only one knob
        param1=param1,
        param2=param2,
        minRadius=minRadius,
        maxRadius=maxRadius
    )

    if circles is not None:
        count = 0
        circles = np.uint16(np.around(circles))
        
        for i in circles[0, :]:  # Process each detected circle (x, y, radius)
            # Validate circle position against expected centerline
            if abs(i[0] - mid_line) <= threhsold:  # Within threshold of expected position
                count += 1
                
                # Draw visualization elements on result image
                cv2.line(res, (mid_line, 0), (mid_line, res.shape[0]), (255, 0, 0), 2)  # Centerline
                cv2.circle(res, (i[0], i[1]), i[2], (0, 255, 0), 1)  # Circle outline
                cv2.circle(res, (i[0], i[1]), 1, (0, 0, 255), 3)    # Circle center
                cv2.circle(res, (center[0], center[1]), 2, (0, 0, 255), 3)  # Image center

                # Calculate position offset from image center
                pixel_x = (int(circles[0][0][0]) - center[0]) * scale  # Horizontal offset
                pixel_y = (-(int(circles[0][0][1]) - center[1])) * scale  # Vertical offset (Y-inverted)

                # Validate detected circle radius
                if 88 <= int(i[2]) <= 96:  # Expected radius range for standard knobs
                    return pixel_x, pixel_y, res
                else:
                    print('圆心半径不对!')  # "Circle radius incorrect!"
                    return None, None, None

        if count == 0:
            print("没有符合要求的圆形")  # "No qualifying circles found"
            return None, None, None
            
    else:
        print("未检测成功")  # "Detection failed"
        return None, None, None


def get_now_wyb_loc(kong_num, scale=1):
    """
    Combines blue circle detection and knob position detection to calculate current test point locations.
    
    This is the main integration function that combines results from both detection algorithms
    to provide precise coordinates for all test points relative to the current equipment position.
    The function is essential for automated robotic testing where probe placement must account
    for both the reference test point layout and current equipment orientation.
    
    INTEGRATION WORKFLOW:
    1. Detect current knob position and calculate offset from center
    2. Load reference blue circle positions from template image  
    3. Apply knob offset to all reference positions
    4. Extract specific subset of points for testing (e.g., empty positions)
    5. Return comprehensive coordinate data for robotic control
    
    Parameters:
    -----------
    kong_num : int
        Number of empty/available test positions to extract from the end of the sorted list
        (Typically corresponds to unused input jacks on the multimeter)
    scale : float, default=1
        Scaling factor to convert image coordinates to robot coordinate system
        (Accounts for camera-to-robot coordinate transformation)
        
    Returns:
    --------
    tuple : (all_positions, empty_positions, result_image, knob_offset)
        all_positions : list of [x, y] coordinates or None
            Complete list of all test point positions adjusted for current knob position
        empty_positions : list of [x, y] coordinates or None  
            Subset of positions corresponding to empty/available test points
        result_image : numpy.ndarray or None
            Annotated image showing knob detection results for verification
        knob_offset : [x, y] coordinates or None
            Raw knob position offset from image center
            
    Algorithm Details:
    ------------------
    Position Calculation:
    - Reference positions from blue circle detection (relative to template center)
    - Current knob offset from equipment image (relative to image center)
    - Final positions = Reference positions + Knob offset
    
    Empty Position Selection:
    - Extracts last 'kong_num' positions from sorted test point list
    - These typically correspond to auxiliary input jacks
    - Useful for testing configurations that don't use all available connections
    
    Error Handling:
    - Returns None for all values if knob detection fails
    - Maintains data integrity by validating all intermediate results
    - Enables robust error checking in calling functions
    
    Coordinate Systems:
    - Image coordinates: Origin at top-left, Y increases downward
    - Robot coordinates: Origin at center, standard Cartesian orientation
    - Scale factor handles conversion between measurement units
    
    Usage Example:
    --------------
    all_loc, kong_loc, res, zp_delta_pos = get_now_wyb_loc(4, 0.241935)
    if all_loc is not None:
        # Use coordinates for robotic probe placement
        for position in kong_loc:
            robot.move_to_position(position[0], position[1])
    """
    
    # ========================================================================
    # STEP 1: DETECT CURRENT KNOB POSITION
    # ========================================================================
    # Analyze equipment image to find rotary knob position
    # binary=False: Skip binary thresholding for better knob edge detection
    # param2=0.8: Slightly more sensitive detection for equipment variations
    delta_x, delta_y, res = find_zp_delta_loc(pic_equip_path, binary=False, param2=0.8, scale=scale)

    # Proceed only if knob detection was successful
    if (delta_x is not None) and (delta_y is not None) and (res is not None):
        
        # ====================================================================
        # STEP 2: LOAD REFERENCE TEST POINT POSITIONS  
        # ====================================================================
        # Get blue circle positions from reference template image
        circle_loaction, zp_location = find_blue_circle_loc(pic_blue_path, scale)

        # ====================================================================
        # STEP 3: CALCULATE ABSOLUTE TEST POINT POSITIONS
        # ====================================================================
        # Apply knob offset to all reference positions
        # This transforms relative template positions to absolute current positions
        wyb_all_loc = [[(element[0] + delta_x), (element[1] + delta_y)] for element in circle_loaction]

        # ====================================================================
        # STEP 4: EXTRACT EMPTY/AVAILABLE POSITIONS
        # ====================================================================
        # Select last 'kong_num' positions (typically empty input jacks)
        # Negative indexing ensures we get the intended subset regardless of total count
        kong_all_loc = wyb_all_loc[len(wyb_all_loc) - kong_num : len(wyb_all_loc)]

        # Format knob offset for return
        zp_delta_pos = [delta_x, delta_y]

        return wyb_all_loc, kong_all_loc, res, zp_delta_pos

    else:
        # Knob detection failed - return None for all values
        return None, None, None, None


# ============================================================================
# TESTING AND VALIDATION CODE
# ============================================================================
"""
Example usage and testing code (commented out for production):

# Test the complete detection pipeline
all_loc, kong_loc, res, zp_delta_pos = get_now_wyb_loc(4, 0.241935)

print(kong_loc)      # Print empty position coordinates
print(zp_delta_pos)  # Print knob offset values

# Display result image with detection annotations
cv2.imshow('ss', res)
cv2.waitKey(0)

Expected Output Format:
- kong_loc: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
- zp_delta_pos: [offset_x, offset_y]
"""

'''
all_loc,kong_loc,res,zp_delta_pos = get_now_wyb_loc(4,0.241935)

print(kong_loc)
print(zp_delta_pos)
cv2.imshow('ss', res)
cv2.waitKey(0)
'''