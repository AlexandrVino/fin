import pygame
import requests
import sys
import os
import math

# Подобранные константы для поведения карты.
LAT_STEP = 0.008  # Шаги при движении карты по широте и долготе
LON_STEP = 0.02
coord_to_geo_x = 0.0000428  # Пропорции пиксельных и географических координат.
coord_to_geo_y = 0.0000428


# Определяем функцию, считающую расстояние между двумя точками, заданными координатами
def lonlat_distance(a, b):
    degree_to_meters_factor = 111 * 1000  # 111 километров в метрах
    a_lon, a_lat = a
    b_lon, b_lat = b

    # Берем среднюю по широте точку и считаем коэффициент для нее.
    radians_lattitude = math.radians((a_lat + b_lat) / 2.)
    lat_lon_factor = math.cos(radians_lattitude)

    # Вычисляем смещения в метрах по вертикали и горизонтали.
    dx = abs(a_lon - b_lon) * degree_to_meters_factor * lat_lon_factor
    dy = abs(a_lat - b_lat) * degree_to_meters_factor

    # Вычисляем расстояние между точками.
    distance = math.sqrt(dx * dx + dy * dy)

    return distance


# Найти объект по координатам.
def reverse_geocode(ll):
    geocoder_request_template = "http://geocode-maps.yandex.ru/1.x/?apikey=40d1649f-0493-4b70-98ba-98533de7710b&geocode={ll}&format=json"

    # Выполняем запрос к геокодеру, анализируем ответ.
    geocoder_request = geocoder_request_template.format(**locals())
    response = requests.get(geocoder_request)

    if not response:
        raise RuntimeError(
            """Ошибка выполнения запроса:
            {request}
            Http статус: {status} ({reason})""".format(
                request=geocoder_request, status=response.status_code, reason=response.reason))

    # Преобразуем ответ в json-объект
    json_response = response.json()

    # Получаем первый топоним из ответа геокодера.
    features = json_response["response"]["GeoObjectCollection"]["featureMember"]
    return features[0]["GeoObject"] if features else None


def reverse_geocode_by_address(address):
    toponym_to_find = address

    geocoder_api_server = "http://geocode-maps.yandex.ru/1.x/"

    geocoder_params = {
        "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
        "geocode": toponym_to_find,
        "format": "json"}

    response = requests.get(geocoder_api_server, params=geocoder_params)

    if not response:
        raise RuntimeError(
            """Ошибка выполнения запроса:
            {request}
            Http статус: {status} ({reason})""".format(
                request=geocoder_request, status=response.status_code, reason=response.reason))

    # Преобразуем ответ в json-объект
    json_response = response.json()

    # Получаем первый топоним из ответа геокодера.
    features = json_response["response"]["GeoObjectCollection"]["featureMember"]
    return features[0]["GeoObject"] if features else None


# Структура для хранения результатов поиска:
# координаты объекта, его название и почтовый индекс, если есть.

class SearchResult(object):
    def __init__(self, point, address=None, postal_code=None):
        self.point = point
        self.address = address
        self.postal_code = postal_code


class Button:
    def __init__(self, x, y, width, height, text):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = '#94a2b0'
        self.active_color = '#59d770'
        self.text_color = '#000000'
        self.text = text
        self.is_active = False
        self.font = pygame.font.Font(None, 35)
        self.image = pygame.Surface((width, height))
        self.set_state(text == 'map')
        self.rect = pygame.Rect(x, y, 20, 20)

    def draw(self, screen):
        screen.blit(self.image, [self.x, self.y])

    def add_button_text(self, screen):
        text = self.font.render(self.text, True, self.text_color)
        text_x = self.width // 2 - text.get_width() // 2
        text_y = self.height // 2 - text.get_height() // 2
        screen.blit(text, (text_x, text_y))

    def set_state(self, flag):
        self.is_active = flag
        if self.is_active:
            pygame.draw.rect(self.image, pygame.Color(self.active_color), [0, 0,
                                                                           self.width, self.height])
            self.add_button_text(self.image)
        else:
            pygame.draw.rect(self.image, pygame.Color(self.color), [0, 0,
                                                                    self.width, self.height])
            self.add_button_text(self.image)

    def check_pos(self, pos):
        return self.x <= pos[0] <= self.x + self.width and self.y <= pos[1] <= self.y + self.height


class InputBox:
    def __init__(self, x, y, w, h, color, active_color, text=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = color
        self.color_base = color
        self.active_color = active_color

        self.text = text
        self.font = pygame.font.Font(None, 30)
        self.txt_surface = self.font.render(text, True, self.color)
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # If the user clicked on the input_box rect.
            if self.rect.collidepoint(event.pos):
                # Toggle the active variable.
                self.active = not self.active
            else:
                self.active = False
            # Change the current color of the input box.
            self.color = self.active_color if self.active else self.color_base
        if event.type == pygame.KEYDOWN:
            if self.active:

                if event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    key = event.__str__().split('{')[1].split('}')[0].split(', ')[0].split(": '")[1][:-1]
                    if key in '123456789- _qwertyuiopasdfghjklzxcvbnmйцукенгшщзхъэждлорпавыфячсмитьбю,':
                        self.text += key
                # Re-render the text.
                self.txt_surface = self.font.render(self.text[:17], True, self.color)

    def draw(self, screen):
        # Blit the text.
        screen.blit(self.txt_surface, (self.rect.x + 5, self.rect.y + 5))
        # Blit the rect.
        pygame.draw.rect(screen, self.color, self.rect, 2)


# Параметры отображения карты:
# координаты, масштаб, найденные объекты и т.д.


class MapParams(object):
    # Параметры по умолчанию.
    def __init__(self):
        self.lat = 58.010450  # Координаты центра карты на старте.
        self.lon = 56.229434
        self.zoom = 14  # Масштаб карты на старте.
        self.type = "map"  # Тип карты на старте.

        self.search_result = None  # Найденный объект для отображения на карте.
        self.use_postal_code = False
        self.buttons = [
            Button(230, 5, 100, 40, 'sat'),
            Button(340, 5, 100, 40, 'map'),
            Button(450, 5, 100, 40, 'trf'),
            Button(560, 5, 100, 40, 'skl')
        ]
        self.input_box = InputBox(10, 5, 200, 40, '#ffffff', '#000000')

    # Преобразование координат в параметр ll
    def ll(self):
        return "{0},{1}".format(self.lon, self.lat)

    # Обновление параметров карты по нажатой клавише.
    def update(self, event):
        if event.key == pygame.K_PAGEUP and self.zoom < 19:  # PG_UP
            self.zoom += 1
        elif event.key == pygame.K_PAGEDOWN and self.zoom > 2:  # PG_DOWN
            self.zoom -= 1
        elif event.key == pygame.K_LEFT:  # LEFT_ARROW
            self.lon -= LON_STEP * math.pow(2, 15 - self.zoom)
            if self.lon < 0:
                self.lon = 180
        elif event.key == pygame.K_RIGHT:  # RIGHT_ARROW
            self.lon += LON_STEP * math.pow(2, 15 - self.zoom)
            if self.lon >= 180:
                self.lon = 180 - self.lon
        elif event.key == pygame.K_UP and self.lat < 85:  # UP_ARROW
            self.lat += LAT_STEP * math.pow(2, 15 - self.zoom)
            if self.lat >= 90:
                self.lat = 90 - self.lat
        elif event.key == pygame.K_DOWN and self.lat > -85:  # DOWN_ARROW
            self.lat -= LAT_STEP * math.pow(2, 15 - self.zoom)
            if self.lat < 0:
                self.lat = abs(self.lat) - 90
        elif event.key == pygame.K_RETURN:  # DOWN_ARROW
            if self.input_box.text:
                data = reverse_geocode_by_address(self.input_box.text)
                if data is not None:
                    data = [
                        data["Point"]["pos"].split(' '),
                    ]
                    self.search_result = SearchResult(*data)
                    self.lon, self.lat = float(self.search_result.point[0]), float(self.search_result.point[1])


# Создание карты с соответствующими параметрами.
def load_map(mp):
    geocoder_params = {
        "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
        'll': mp.ll(),
        'z': mp.zoom,
        'type': mp.type,
        'l': mp.type
    }
    geocoder_api_server = "http://static-maps.yandex.ru/1.x/"
    if mp.search_result:
        geocoder_params['pt'] = "{0},{1},pm2grm".format(mp.search_result.point[0],
                                                        mp.search_result.point[1])
    response = requests.get(geocoder_api_server, params=geocoder_params)

    if not response:
        print("Ошибка выполнения запроса:")
        print(response.url)
        print("Http статус:", response.status_code, "(", response.reason, ")")
        sys.exit(1)

    # Запишем полученное изображение в файл.
    map_file = "map.png"
    try:
        with open(map_file, "wb") as file:
            file.write(response.content)
    except IOError as ex:
        print("Ошибка записи временного файла:", ex)
        sys.exit(2)

    return map_file


def main():
    # Инициализируем pygame
    pygame.init()
    screen = pygame.display.set_mode((700, 500))
    screen.fill('#b6c5b9')

    # Заводим объект, в котором будем хранить все параметры отрисовки карты.
    mp = MapParams()
    map_file = load_map(mp)
    screen.blit(pygame.image.load(map_file), (50, 50))
    for button in mp.buttons:
        button.draw(screen)
    mp.input_box.draw(screen)
    pygame.display.flip()

    while True:
        event = pygame.event.wait()
        if event.type == pygame.QUIT:  # Выход из программы
            break
        elif event.type == pygame.KEYDOWN:  # Обрабатываем различные нажатые клавиши.
            mp.update(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            button_active = [button for button in mp.buttons if button.is_active][0]
            for button in mp.buttons:
                if button.check_pos(event.pos) and button is not button_active:
                    button.set_state(True)
                    button_active.set_state(False)
                    mp.type = button.text if button.text in ('map', 'sat') else mp.type + f',{button.text}'
        else:
            continue
        mp.input_box.handle_event(event)

        # Загружаем карту, используя текущие параметры.
        screen.fill('#b6c5b9')
        mp.input_box.draw(screen)

        map_file = load_map(mp)

        # Рисуем картинку, загружаемую из только что созданного файла.
        screen.blit(pygame.image.load(map_file), (50, 50))

        for button in mp.buttons:
            button.draw(screen)
        pygame.display.flip()

    pygame.quit()
    # Удаляем за собой файл с изображением.
    os.remove(map_file)


if __name__ == "__main__":
    main()
