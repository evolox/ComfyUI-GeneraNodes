import cv2
import numpy as np

from image_transformer import ImageTransformer

class OpenCVApp:
    # Константы конфигурации
    MAX_SIZE = 512
    PADDING = 50
    POINT_RADIUS = 5
    POINT_COLOR = (0, 0, 255)  # Красный
    POLYLINE_COLOR = (0, 255, 0)  # Зеленый
    POLYLINE_THICKNESS = 2
    SYNC_TOGGLE_KEY = ord('s')
    RESET_KEY = ord('r')
    EXIT_KEY = 27  # Клавиша ESC
    CLICK_THRESHOLD = 10  # Порог для определения выбора точки
    EXTRA_SPACE = 150  # Дополнительное пространство для инструкций и информации
    FONT = cv2.FONT_HERSHEY_SIMPLEX
    FONT_SCALE = 0.6
    FONT_COLOR_INSTRUCTIONS = (255, 255, 255)  # Белый
    FONT_COLOR_COORDS = (0, 255, 0)  # Зеленый
    FONT_COLOR_MATRIX = (255, 255, 0)  # Голубой
    TEXT_THICKNESS = 1
    TEXT_START_Y = 20
    TEXT_LINE_HEIGHT = 20

    def __init__(self, image_transformer: ImageTransformer):
        self.pts = np.array([], dtype=np.float32)
        self.initial_pts = np.array([], dtype=np.float32)
        self.dragging_point = -1
        self.sync_points = True
        self.image_transformer = image_transformer
        # Уменьшаем или увеличиваем изображение
        self.image_transformer.resize_image(self.MAX_SIZE)
        # Обрабатываем отступы в OpenCVApp
        self.padding = self.PADDING
        self.add_padding()
        # Инициализируем точки
        self.initialize_points()

    def add_padding(self):
        resized_image = self.image_transformer.get_resized_image()
        self.image_with_padding = cv2.copyMakeBorder(
            resized_image, self.padding, self.padding, self.padding, self.padding,
            cv2.BORDER_CONSTANT, value=[0, 0, 0]
        )

    def mouse_callback(self, event, x, y, flags, param):
        # Приводим координаты x и y к системе координат без отступов
        x_adj = x - self.padding
        y_adj = y - self.padding

        if event == cv2.EVENT_LBUTTONDOWN:
            # Проверяем, близка ли точка к существующей
            for i, pt in enumerate(self.pts):
                if abs(x_adj - pt[0]) < self.CLICK_THRESHOLD and abs(y_adj - pt[1]) < self.CLICK_THRESHOLD:
                    self.dragging_point = i
                    break

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.dragging_point != -1:
                # Перемещаем выбранную точку
                self.pts[self.dragging_point] = [x_adj, y_adj]
                width = param.shape[1] - 2 * self.padding
                x_center = width / 2

                if self.sync_points:
                    idx_other = self.get_synchronized_index(self.dragging_point)
                    if idx_other != -1:
                        delta_x = x_adj - x_center
                        self.pts[idx_other][0] = x_center - delta_x
                        self.pts[idx_other][1] = y_adj

        elif event == cv2.EVENT_LBUTTONUP:
            self.dragging_point = -1

    def get_synchronized_index(self, index):
        """Получаем индекс точки для синхронизации."""
        if index in [0, 1]:
            return 1 - index
        elif index in [2, 3]:
            return 5 - index
        return -1

    def reset_points(self):
        self.pts = self.initial_pts.copy()

    def toggle_sync(self):
        self.sync_points = not self.sync_points
        print("Синхронизация точек:", "Включена" if self.sync_points else "Отключена")

    def initialize_points(self):
        resized_image = self.image_transformer.get_resized_image()
        resized_height, resized_width = resized_image.shape[:2]
        # Инициализируем точки без учета отступов
        self.pts = np.array([
            [0, 0],  # Верхний левый угол
            [resized_width - 1, 0],  # Верхний правый угол
            [resized_width - 1, resized_height - 1],  # Нижний правый угол
            [0, resized_height - 1]  # Нижний левый угол
        ], dtype=np.float32)
        self.initial_pts = self.pts.copy()

    def draw_text(self, canvas, text, position, color):
        """Функция для отображения текста на холсте."""
        cv2.putText(
            canvas,
            text,
            position,
            self.FONT,
            self.FONT_SCALE,
            color,
            self.TEXT_THICKNESS
        )

    def draw_display(self, combined, M, width, height):
        canvas_height = combined.shape[0] + self.EXTRA_SPACE
        canvas_width = combined.shape[1]
        canvas = np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8)
        canvas[:combined.shape[0], :combined.shape[1]] = combined

        y_offset = combined.shape[0] + self.TEXT_START_Y

        # Инструкции
        instructions = [
            f"Press 'S' to toggle sync points (current: {'ON' if self.sync_points else 'OFF'})",
            "Press 'R' to reset points",
            "Press 'ESC' to exit"
        ]
        for i, text in enumerate(instructions):
            self.draw_text(
                canvas,
                text,
                (10, y_offset + i * self.TEXT_LINE_HEIGHT),
                self.FONT_COLOR_INSTRUCTIONS
            )

        # Отображаем координаты точек (без учета отступа)
        for i, pt in enumerate(self.pts):
            coord_text = f"Pt{i}: ({pt[0]:.1f}, {pt[1]:.1f})"
            self.draw_text(
                canvas,
                coord_text,
                (int(canvas_width / 2), y_offset + i * self.TEXT_LINE_HEIGHT),
                self.FONT_COLOR_COORDS
            )

        # Отображаем матрицу преобразования
        self.draw_text(
            canvas,
            "Transformation Matrix:",
            (10, y_offset + 60),
            self.FONT_COLOR_MATRIX
        )
        for i in range(3):
            m_text = f"{M[i, 0]:.4f}, {M[i, 1]:.4f}, {M[i, 2]:.4f}"
            self.draw_text(
                canvas,
                m_text,
                (10, y_offset + 80 + i * self.TEXT_LINE_HEIGHT),
                self.FONT_COLOR_MATRIX
            )

        return canvas

    def run(self):
        image_with_padding = self.image_with_padding
        height, width = image_with_padding.shape[:2]
        resized_image = self.image_transformer.get_resized_image()
        resized_height, resized_width = resized_image.shape[:2]

        cv2.namedWindow('Image', cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
        cv2.setMouseCallback('Image', self.mouse_callback, param=image_with_padding)

        while True:
            display_image = image_with_padding.copy()

            # Смещаем точки для отображения на изображении с отступами
            display_pts = self.pts + np.array([self.padding, self.padding])

            # Рисуем полигон и точки
            cv2.polylines(
                display_image,
                [display_pts.astype(int)],
                isClosed=True,
                color=self.POLYLINE_COLOR,
                thickness=self.POLYLINE_THICKNESS
            )
            for pt in display_pts:
                cv2.circle(
                    display_image,
                    tuple(pt.astype(int)),
                    self.POINT_RADIUS,
                    self.POINT_COLOR,
                    -1
                )

            # Перспективное преобразование
            src_pts = self.initial_pts.copy()
            dst_pts = self.pts.copy()
            M = cv2.getPerspectiveTransform(src_pts, dst_pts)

            # Применяем преобразование с использованием ImageTransformer
            transformed_image = self.image_transformer.get_transformed_image(M, (resized_width, resized_height))

            # Добавляем отступы обратно
            transformed_image_with_padding = cv2.copyMakeBorder(
                transformed_image, self.padding, self.padding, self.padding, self.padding,
                cv2.BORDER_CONSTANT, value=[0, 0, 0]
            )

            # Убеждаемся, что трансформированное изображение не превышает размеры уменьшенного
            transformed_image_with_padding = cv2.resize(
                transformed_image_with_padding, (width, height), interpolation=cv2.INTER_AREA
            )

            # Объединение изображений
            combined = np.hstack((display_image, transformed_image_with_padding))
            canvas = self.draw_display(combined, M, width, height)

            cv2.imshow('Image', canvas)

            key = cv2.waitKey(1) & 0xFF

            if key == self.EXIT_KEY:  # Клавиша ESC
                break
            elif key == self.SYNC_TOGGLE_KEY:
                self.toggle_sync()
            elif key == self.RESET_KEY:
                self.reset_points()
                print("Точки сброшены в исходное положение.")

        cv2.destroyAllWindows()

if __name__ == "__main__":
    image_transformer = ImageTransformer()
    image_transformer.load_image("input.jpg")
    app = OpenCVApp(image_transformer)
    app.run()