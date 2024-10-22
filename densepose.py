import cv2
import numpy as np

class HumanHeightDetector:
    def __init__(self, cv_image):
        self.cv_image = cv_image
        self.top = None
        self.bottom = None
        self.head_bottom = None
        
        self._noise_offset = 5
        
    def do_measurments(self):
        self._find_top()
        self._find_head_bottom()
        self._find_bottom()
        
        return (self.top, self.bottom, self.head_bottom)
    
    def _find_top(self):
        height, width = self.cv_image.shape[:2]
        center_x = width // 2
        for y in range(0, height): # starting from center find first non-black
            pixel_value = self.cv_image[y, center_x]
            if np.any(pixel_value != 0):
                break
        if y >= height - self._noise_offset:
            raise ValueError("Error in head size estimation algorithm")
        self.top = (center_x, y)
    
    def _find_head_bottom(self):
        if self.top is None:
            self._find_top()
            
        TAG_COLOR = (250, 250, 250)
        working_image = self.cv_image.copy()
        
        point = self.top[0], self.top[1] + self._noise_offset # for avoid bugs in contour of image
        cv2.floodFill(working_image, None, point, TAG_COLOR, (0, 0, 0), (10, 10, 10))
        
        head_zone = cv2.inRange(working_image, TAG_COLOR, TAG_COLOR)
        contours, _ = cv2.findContours(head_zone, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        self.head_bottom = max(contours[0], key=lambda point: point[0][1])[0]

    def _find_bottom(self):
        height, width = self.cv_image.shape[:2]
        center_x = width // 2
        for y in range(height - 1, -1, -1):
            if np.any(self.cv_image[y, : width - self._noise_offset] > 0):
                break
        self.bottom = (center_x, y)

    def visualize(self):
        """Visualize the height and head height."""
        HEIGHT_COLOR = (0, 200, 128)
        TEXT_COLOR = (0, 0, 255)
        HEAD_COLOR = (255, 255, 128)
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        img_to_show = self.cv_image.copy()

        height, width = img_to_show.shape[:2]
        top, bottom, head_bottom = self.top[1], self.bottom[1], self.head_bottom[1]
        human_height = bottom - top
        if human_height:
            cv2.line(img_to_show, (0, top), (width - 1, top), HEIGHT_COLOR, 2)
            cv2.line(img_to_show, (0, bottom), (width - 1, bottom), HEIGHT_COLOR, 2)
            cv2.line(img_to_show, (50, top), (50, bottom), HEIGHT_COLOR, 2)
            cv2.putText(img_to_show, f'{human_height}px', (3, (top + bottom) // 2), font, 1, TEXT_COLOR, 2, cv2.LINE_AA)

        # Draw head height line
        head_height = head_bottom - top
        center_x = width // 2
        if head_height:
            cv2.line(img_to_show, (0, head_bottom), (width - 1, head_bottom), HEAD_COLOR, 2)
            cv2.line(img_to_show, (center_x, top), (center_x, head_bottom), HEAD_COLOR, 2)
            cv2.putText(img_to_show, f'{head_height}px', (center_x + 10, (top + head_bottom) // 2), font, 1, TEXT_COLOR, 2, cv2.LINE_AA)

        return img_to_show


if __name__ == "__main__":
    img = cv2.imread("densepose.png")
    detector = HumanHeightDetector(img)
    detector.do_measurments()
    
    result = detector.visualize()
    cv2.imshow('Human and Head Height', result)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
