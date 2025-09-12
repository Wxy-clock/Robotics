#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Processing Module for Multimeter Recognition

This module provides computer vision functionality for automated multimeter testing,
including QR code recognition, LCD digit recognition, and image preprocessing.

The module contains the following main functions:
- LCD screen detection and digit recognition
- QR code detection and decoding
- Image preprocessing and enhancement
- Coordinate system transformations

Dependencies:
    - OpenCV (cv2)
    - NumPy
    - PIL (Python Imaging Library)
    - PyTorch (for neural network digit recognition)
    - pyzbar (for QR code recognition)
    - ultralytics (for YOLO model support)
"""

import os
import threading
import time
from pathlib import Path

# Third-party imports
import cv2
import numpy as np
import torch
from PIL import Image
import imutils
from pyzbar import pyzbar

# PyTorch model imports - Fixed to use ultralytics instead of missing YOLOv5 modules
try:
    from ultralytics import YOLO
    from ultralytics.utils.torch_utils import select_device
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    print("Warning: ultralytics not available. Neural network digit recognition will be disabled.")
    ULTRALYTICS_AVAILABLE = False
    
    # Fallback dummy functions
    def select_device():
        return 'cpu'

# Constants
BLACK_IMAGE_PATH = "C:/banshouGUI/pic_linshi/black_image.png"
RECOGNITION_RESULT_PATH = "C:/banshouGUI/pic_linshi/shibie.png"
SCREEN_MODE = 1

# Global variables for digit recognition results
original_results = []  # Store original recognition results
processed_results = []  # Store processed recognition results


def detect_lcd_screen(source_image):
    """
    Detect and extract LCD screen area from the source image.
    
    This function uses edge detection and contour analysis to locate
    the LCD screen in the input image and extract it as a separate image.
    
    Args:
        source_image (numpy.ndarray): Input image containing LCD screen
        
    Returns:
        numpy.ndarray: Extracted and rotated LCD screen image
    """
    # Create morphological kernel
    morphology_kernel = np.ones((3, 3), np.uint8)
    
    # Convert to grayscale
    gray_image = cv2.cvtColor(source_image.copy(), cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred_image = cv2.GaussianBlur(gray_image, (3, 3), 0)
    median_filtered = cv2.medianBlur(blurred_image, 3)
    
    # Edge detection
    edges = cv2.Canny(median_filtered, 20, 100)
    
    # Dilate edges to connect nearby contours
    dilated_edges = cv2.dilate(edges, morphology_kernel, iterations=1)
    
    # Second edge detection on dilated image
    final_edges = cv2.Canny(dilated_edges, 10, 240)
    
    # Find contours for LCD boundary detection
    contours, hierarchy = cv2.findContours(final_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Find the largest contour (assumed to be LCD screen)
    max_contour = max(contours, key=cv2.contourArea)
    
    # Create mask image
    mask_image = np.zeros((source_image.shape[0], source_image.shape[1]), dtype=np.uint8)
    
    # Fill the largest contour to create extraction mask
    filled_mask = cv2.drawContours(mask_image.copy(), [max_contour], -1, (255, 255, 255), -1)
    
    # Find minimum area rectangle and rotation angle
    min_area_rect = cv2.minAreaRect(max_contour)
    rotation_angle = min_area_rect[2]
    
    # Normalize rotation angle
    if rotation_angle > 45:
        rotation_angle = rotation_angle - 90
    if rotation_angle < -45:
        rotation_angle = rotation_angle + 90
    
    # Rotate both mask and original image
    rotated_mask = imutils.rotate(filled_mask.copy(), angle=rotation_angle)
    rotated_original = imutils.rotate(source_image.copy(), angle=rotation_angle)
    
    # Find bounding box of rotated mask
    edges_rotated = cv2.Canny(rotated_mask.copy(), 250, 255)
    
    contours_rotated, _ = cv2.findContours(edges_rotated, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    max_contour_rotated = max(contours_rotated, key=cv2.contourArea)
    
    # Get bounding rectangle coordinates
    bounding_rect = cv2.minAreaRect(max_contour_rotated)
    box_points = cv2.boxPoints(bounding_rect)
    box_points = np.intp(box_points)
    
    # Extract bounding coordinates
    x_min = min(box_points[:, 0])
    x_max = max(box_points[:, 0])
    y_min = min(box_points[:, 1])
    y_max = max(box_points[:, 1])
    
    # Extract LCD region
    extracted_lcd = rotated_original[y_min:y_max, x_min:x_max]
    
    return extracted_lcd


def recognize_single_digit(digit_image, reference_digit):
    """
    Recognize a single digit using contour analysis and pattern matching.
    
    This function analyzes the contours of a digit image and matches them
    against known digit patterns to identify the digit.
    
    Args:
        digit_image (numpy.ndarray): Image containing single digit
        reference_digit (int): Reference digit for comparison
        
    Returns:
        str: Recognized digit as string
    """
    # Apply median filtering
    filtered_image = cv2.medianBlur(digit_image, 3)
    filtered_image = cv2.medianBlur(filtered_image, 3)
    
    # Convert to grayscale
    gray_image = cv2.cvtColor(filtered_image, cv2.COLOR_BGR2GRAY)
    
    # Find minimum brightness value and subtract it
    min_brightness = np.min(gray_image)
    normalized_gray = gray_image - min_brightness
    
    # Calculate average brightness
    average_brightness = np.mean(normalized_gray)
    
    # Edge detection
    edges = cv2.Canny(normalized_gray, 10, 50)
    
    # Find and filter contours
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    
    # Filter contours by length
    filtered_contours = []
    min_contour_length = digit_image.shape[1] * 0.4
    for contour in contours:
        contour_length = cv2.arcLength(contour, False)
        if contour_length >= min_contour_length:
            filtered_contours.append(contour)
    
    # Create binary image with filtered contours
    contour_image = np.zeros((edges.shape[0], edges.shape[1]), dtype=np.uint8)
    cv2.drawContours(contour_image, filtered_contours, -1, (255, 255, 255), 1)
    
    # Define geometric regions for digit analysis
    image_height, image_width = digit_image.shape[:2]
    center_y = int(image_width * 0.5)
    upper_boundary = int(image_height * 0.3333)
    lower_boundary = int(image_height * 0.6666)
    
    # Initialize segment detection flags
    segments = [0] * 7  # 7-segment display
    
    # Analyze each segment region
    segment_results = _analyze_digit_segments(contour_image, center_y, upper_boundary, 
                                            lower_boundary, image_height, image_width)
    
    # Pattern matching for digit recognition
    digit_patterns = {
        (0, 1, 1, 0, 0, 0, 0): '1',
        (1, 1, 0, 1, 1, 0, 1): '2',
        (1, 1, 1, 1, 0, 0, 1): '3',
        (0, 1, 1, 0, 0, 1, 1): '4',
        (1, 0, 1, 1, 0, 1, 1): '5',
        (1, 0, 1, 1, 1, 1, 1): '6',
        (1, 1, 1, 0, 0, 0, 0): '7',
        (1, 1, 1, 0, 0, 1, 0): '7',  # Alternative pattern for 7
        (1, 1, 1, 1, 1, 1, 1): '8',
        (1, 1, 1, 1, 0, 1, 1): '9'
    }
    
    # Match pattern and return result
    pattern_tuple = tuple(segment_results)
    recognized_digit = digit_patterns.get(pattern_tuple, str(reference_digit))
    
    return recognized_digit


def _analyze_digit_segments(contour_image, center_y, upper_boundary, lower_boundary, 
                          image_height, image_width):
    """
    Analyze 7-segment display regions to detect active segments.
    
    Args:
        contour_image: Binary image with digit contours
        center_y: Center Y coordinate
        upper_boundary: Upper boundary for segments
        lower_boundary: Lower boundary for segments
        image_height: Image height
        image_width: Image width
        
    Returns:
        list: List of 7 binary values representing segment states
    """
    segments = [0] * 7
    
    # Segment 1: Top horizontal (upper half, center vertical)
    transition_count = 0
    for i in range(upper_boundary):
        if i >= 1 and contour_image[i-1, center_y] == 255 and contour_image[i, center_y] == 0:
            transition_count += 1
            if transition_count >= 2:
                segments[0] = 1
                break
    
    # Segment 2: Upper right (upper boundary, right half)
    transition_count = 0
    for i in range(center_y, image_width):
        if i >= 1 and contour_image[upper_boundary, i-1] == 255 and contour_image[upper_boundary, i] == 0:
            transition_count += 1
            if transition_count >= 2:
                segments[1] = 1
                break
    
    # Segment 3: Lower right (lower boundary, right half)
    transition_count = 0
    for i in range(center_y, image_width):
        if i >= 1 and contour_image[lower_boundary, i-1] == 255 and contour_image[lower_boundary, i] == 0:
            transition_count += 1
            if transition_count >= 2:
                segments[2] = 1
                break
    
    # Segment 4: Bottom horizontal (lower half, center vertical)
    transition_count = 0
    for i in range(lower_boundary, image_height):
        if i >= 1 and contour_image[i-1, center_y] == 255 and contour_image[i, center_y] == 0:
            transition_count += 1
            if transition_count >= 2:
                segments[3] = 1
                break
    
    # Segment 5: Lower left (lower boundary, left half)
    transition_count = 0
    for i in range(0, center_y):
        if i >= 1 and contour_image[lower_boundary, i-1] == 255 and contour_image[lower_boundary, i] == 0:
            transition_count += 1
            if transition_count >= 2:
                segments[4] = 1
                break
    
    # Segment 6: Upper left (upper boundary, left half)
    transition_count = 0
    for i in range(0, center_y):
        if i >= 1 and contour_image[upper_boundary, i-1] == 255 and contour_image[upper_boundary, i] == 0:
            transition_count += 1
            if transition_count >= 2:
                segments[5] = 1
                break
    
    # Segment 7: Middle horizontal (center, center vertical)
    transition_count = 0
    for i in range(upper_boundary, lower_boundary):
        if i >= 1 and contour_image[i-1, center_y] == 255 and contour_image[i, center_y] == 0:
            transition_count += 1
            if transition_count >= 2:
                segments[6] = 1
                break
    
    return segments


def recognize_digits_neural_network(image_path, rotation_angle=-9, processing_mode=1):
    """
    Recognize digits using neural network model.
    
    This function uses a pre-trained PyTorch model to recognize digits
    in the LCD display image.
    
    Args:
        image_path (str): Path to the image file
        rotation_angle (float): Rotation angle for image correction
        processing_mode (int): Processing mode (0 or 1)
        
    Returns:
        str: Recognized digit string or error message
    """
    if not ULTRALYTICS_AVAILABLE:
        print("Neural network recognition not available. Using fallback method.")
        return "ERROR: Neural network not available"
    
    try:
        # Load pre-trained model using ultralytics
        weights_path = 'D:/new_wyb_sys/do_image/num_best_L.pt'
        
        # Check if model file exists
        if not os.path.exists(weights_path):
            print(f"Model file not found: {weights_path}")
            return "ERROR: Model file not found"
        
        # Load model with ultralytics
        model = YOLO(weights_path)
        device = select_device()
        
        # Model input requirements
        input_height, input_width = 640, 640
        
        # Load and preprocess image
        original_image = cv2.imread(image_path)
        
        if original_image is None:
            return "ERROR: Could not load image"
        
        # Standardize image size
        new_height = int(1024 * original_image.shape[0] / original_image.shape[1])
        resized_image = cv2.resize(original_image.copy(), (1024, new_height))
        
        # Crop image to focus on LCD area
        crop_left, crop_right = 100, 800
        crop_top, crop_bottom = 200, 800
        cropped_image = resized_image[crop_top:crop_bottom, crop_left:crop_right]
        
        # Rotate image for alignment
        center = (cropped_image.shape[1] // 2, cropped_image.shape[0] // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, rotation_angle, 1.0)
        rotated_image = cv2.warpAffine(cropped_image, rotation_matrix, 
                                      (cropped_image.shape[1], cropped_image.shape[0]))
        
        # LCD detection if processing_mode == 0
        if processing_mode == 0:
            detected_lcd = detect_lcd_screen(rotated_image)
            
            if detected_lcd.shape[0] == rotated_image.shape[0]:
                return 'lack_of_form'
            
            if detected_lcd.shape[0] < 200:
                return 'locate_incorrect'
            
            final_image = detected_lcd
        else:
            final_image = rotated_image
        
        # Run inference using ultralytics
        results = model(final_image, conf=0.25, iou=0.45, max_det=5)
        
        # Process detection results
        detection_results = []
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    # Get bounding box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = box.conf[0].cpu().numpy()
                    class_id = box.cls[0].cpu().numpy()
                    
                    if confidence < 0.3 or (class_id - 2) < 0:
                        continue
                    
                    digit_class = class_id - 2
                    detection_results.append((int(x1), int(y1), int(x2), int(y2), digit_class))
        
        # Sort detections by x-coordinate (left to right)
        sorted_detections = sorted(detection_results)
        
        # Extract digit sequence
        digit_sequence = ''
        for i, detection in enumerate(sorted_detections):
            # Skip overlapping detections
            if i > 0 and (detection[0] - sorted_detections[i-1][0]) < 20:
                continue
            
            # Check for overload indicator 'L'
            if detection[4] == 10:
                return '0L'
            
            digit_sequence += str(int(detection[4]))
        
        # Handle leading zeros
        if digit_sequence.startswith('0') and len(digit_sequence) == 4:
            digit_sequence = digit_sequence[1:]
        
        # Check for all zeros (burned out display)
        try:
            if int(digit_sequence) == 0 and len(digit_sequence) == 4:
                return '0000'
        except ValueError:
            pass
        
        return digit_sequence
        
    except Exception as e:
        print(f"Error in neural network recognition: {e}")
        return f"ERROR: {str(e)}"


def _prepare_image_for_inference(image, target_width, target_height):
    """
    Prepare image for neural network inference.
    
    Args:
        image: Input image
        target_width: Target width for model input
        target_height: Target height for model input
        
    Returns:
        torch.Tensor: Preprocessed image tensor
    """
    # Get image dimensions
    height, width = image.shape[:2]
    
    # Resize image maintaining aspect ratio
    if width >= height:
        new_height = int(target_height * image.shape[0] / image.shape[1])
        resized_image = cv2.resize(image.copy(), (target_width, new_height))
        
        # Create padding
        padding_height = target_height - new_height
        black_padding = np.zeros((padding_height, target_width, 3), np.uint8)
        cv2.imwrite(BLACK_IMAGE_PATH, black_padding)
        padding_image = cv2.imread(BLACK_IMAGE_PATH)
        
        # Concatenate vertically
        final_image = cv2.vconcat([resized_image, padding_image])
    else:
        new_width = int(target_width * image.shape[1] / image.shape[0])
        resized_image = cv2.resize(image.copy(), (new_width, target_height))
        
        # Create padding
        padding_width = target_width - new_width
        black_padding = np.zeros((target_height, padding_width, 3), np.uint8)
        cv2.imwrite(BLACK_IMAGE_PATH, black_padding)
        padding_image = cv2.imread(BLACK_IMAGE_PATH)
        
        # Concatenate horizontally
        final_image = cv2.hconcat([resized_image, padding_image])
    
    # Resize to exact target dimensions
    model_input = cv2.resize(final_image, (target_height, target_width))
    
    # Normalize and convert to tensor
    model_input = model_input / 255.0
    model_input = model_input[:, :, ::-1].transpose((2, 0, 1))  # HWC to CHW
    model_input = np.expand_dims(model_input, axis=0)  # Add batch dimension
    model_input_tensor = torch.from_numpy(model_input.copy())
    model_input_tensor = model_input_tensor.to(torch.float32)
    
    return model_input_tensor


def decode_qr_code(image_path):
    """
    Decode QR codes from an image.
    
    Args:
        image_path (str): Path to the image containing QR code
        
    Returns:
        str: Decoded QR code data or 'failure' if no QR code found
    """
    try:
        # Load image
        image = cv2.imread(image_path)
        
        # Convert to RGB for pyzbar
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Decode QR codes
        qr_codes = pyzbar.decode(rgb_image)
        
        if qr_codes:
            # Return first QR code data
            return qr_codes[0].data.decode('utf-8')
        else:
            return 'failure'
            
    except Exception as e:
        print(f"QR code decoding error: {e}")
        return 'failure'


def process_recognition_results(image_paths):
    """
    Process multiple image recognition results.
    
    Args:
        image_paths (list): List of image file paths
    """
    global original_results, processed_results
    
    original_results.clear()
    processed_results.clear()
    
    for path in image_paths:
        image_file_path = f"C:/Users/16667/Desktop/photo_problem/{path}.jpg"
        result = recognize_digits_neural_network(image_file_path)
        
        original_results.append(result)
        
        # Pad short results with leading '1's
        if len(result) == 3:
            result = '1' + result
        elif len(result) == 2:
            result = '11' + result
        elif len(result) == 1:
            result = '111' + result
        
        processed_results.append(result)


# Example usage and testing functions
def test_digit_recognition():
    """Test digit recognition on sample images."""
    test_paths = ['7', '8']
    process_recognition_results(test_paths)
    
    print("Original results:", original_results)
    print("Processed results:", processed_results)


if __name__ == "__main__":
    # Run tests if module is executed directly
    test_digit_recognition()