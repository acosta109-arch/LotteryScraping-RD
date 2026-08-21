from datetime import datetime
from flask import Flask, jsonify, Response, request
from flask_cors import CORS
from bs4 import BeautifulSoup
import requests
import os
import json
import logging

# Configurar logging para ver errores en Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración
TIMEOUT = 15
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def load_html(search_date=None):
    """Carga el HTML de las loterías principales"""
    url1 = "https://loteriasdominicanas.com/"
    url2 = "https://loteriasdominicanas.com/anguila"
    url3 = "https://loteriasdominicanas.com/king-lottery"

    if search_date:
        url1 += f"?date={search_date}"
        url2 += f"?date={search_date}"
        url3 += f"?date={search_date}"
        
    games_blocks = []
    headers = {'User-Agent': USER_AGENT}

    try:
        response1 = requests.get(url1, timeout=TIMEOUT, headers=headers)
        response2 = requests.get(url2, timeout=TIMEOUT, headers=headers)
        response3 = requests.get(url3, timeout=TIMEOUT, headers=headers)
        
        response1.raise_for_status()
        response2.raise_for_status()
        response3.raise_for_status()
        
        soup1 = BeautifulSoup(response1.content, "lxml")
        soup2 = BeautifulSoup(response2.content, "lxml")
        soup3 = BeautifulSoup(response3.content, "lxml")
                
        blocks1 = soup1.find_all("div", class_="game-block")
        games_blocks.extend(blocks1)
        blocks2 = soup2.find_all("div", class_="game-block")
        games_blocks.extend(blocks2)
        blocks3 = soup3.find_all("div", class_="game-block")
        games_blocks.extend(blocks3)
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout loading URLs")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error loading HTML: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in load_html: {e}")
        return []

    return games_blocks


def load_html_name(search_name, search_date=None):
    """Carga el HTML de una lotería específica por nombre"""
    url = f"https://loteriasdominicanas.com/{search_name}"

    if search_date:
        url += f"?date={search_date}"

    games_blocks = []
    headers = {'User-Agent': USER_AGENT}

    try:
        response = requests.get(url, timeout=TIMEOUT, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "lxml")
        blocks = soup.find_all("div", class_="game-block")
        games_blocks.extend(blocks)
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout loading URL: {url}")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error loading HTML for {search_name}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error for {search_name}: {e}")
        return []

    return games_blocks


def load_lottery_data():
    """Carga los datos de lottery.json con manejo de errores"""
    try:
        with open('lottery.json', 'r', encoding='utf-8') as file:
            json_data = file.read()
            return json.loads(json_data)
    except FileNotFoundError:
        logger.error("lottery.json file not found")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in lottery.json: {e}")
        return []
    except Exception as e:
        logger.error(f"Error loading lottery.json: {e}")
        return []


def scraping(search_date=None, search_lotery=None):
    """Scraping principal de loterías"""
    data = load_lottery_data()
    
    if not data:
        return []

    if search_lotery:
        data = [item for item in data if search_lotery.lower() in item["name"].lower()]
    
    if len(data) == 0:
        return data

    games_blocks = load_html(search_date)
    unique_loteries = {}
    
    for game_block in games_blocks:
        title_el = game_block.find("a", "game-title")
        if not title_el:
            continue
            
        title = " ".join(title_el.getText().split()).lower()
         
        filtered_data = [item for item in data if item["name"].lower() == title]
        if len(filtered_data) == 0:
            continue  

        pather_score = game_block.find_all("span", "score")
        date_element = game_block.find("div", "session-date")
        pather_date = date_element.getText().strip() if date_element else "Fecha no disponible"
            
        score = "-".join(span.text.strip() for span in pather_score)

        lottery_id = filtered_data[0]["id"]
        if lottery_id not in unique_loteries:
            block = {
                'id': lottery_id,
                'name': filtered_data[0]["name"],
                'date': pather_date,
                'number': score
            }
            unique_loteries[lottery_id] = block

    return sorted(list(unique_loteries.values()), key=lambda k: k["id"])


def scrapingByName(search_name, search_date=None, search_lotery=None):
    """Scraping de loterías por nombre específico"""
    data = load_lottery_data()
    
    if not data:
        return []

    if search_lotery:
        data = [item for item in data if search_lotery.lower() in item["name"].lower()]
    
    if len(data) == 0:
        return data

    games_blocks = load_html_name(search_name, search_date)
    unique_loteries = {}
    
    for game_block in games_blocks:
        title_el = game_block.find("a", "game-title")
        if not title_el:
            continue
            
        title = " ".join(title_el.getText().split()).lower()

        filtered_data = [item for item in data if item["name"].lower() == title]
        if len(filtered_data) == 0:
            continue  

        pather_score = game_block.find_all("span", "score")
        date_element = game_block.find("div", "session-date")
        pather_date = date_element.getText().strip() if date_element else "Fecha no disponible"
            
        score = "-".join(span.text.strip() for span in pather_score)

        lottery_id = filtered_data[0]["id"]
        if lottery_id not in unique_loteries:
            block = {
                'id': lottery_id,
                'name': filtered_data[0]["name"],
                'date': pather_date,
                'number': score
            }
            unique_loteries[lottery_id] = block

    return sorted(list(unique_loteries.values()), key=lambda k: k["id"])


def json_utf8(data=None):
    """Retorna respuesta JSON con encoding UTF-8"""
    json_string = json.dumps(data, ensure_ascii=False)
    return Response(json_string, content_type='application/json; charset=utf-8')


# Inicializar Flask
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
port = int(os.environ.get("PORT", 5000))


# ==================== RUTAS ====================

@app.route("/", methods=['GET'])
def search_lotery():
    """Endpoint principal - todas las loterías"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scraping(search_date)
    return json_utf8(data)


@app.route("/search", methods=['GET'])
def search_lotery_by_name():
    """Buscar loterías por nombre"""
    search_query = request.args.get('name', None)
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))

    if not search_query:
        return jsonify({"error": "Missing 'name' parameter"}), 400
    
    data = scraping(search_date, search_query) 
    return json_utf8(data)


@app.route("/health", methods=['GET'])
def health_check():
    """Health check para Render"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }), 200


@app.route("/loteria-gana-mas", methods=['GET'])
def search_lotery_gana_mas():
    """Lotería Gana Más"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("loteria-nacional/gana-mas", search_date, "Gana Más")
    return json_utf8(data)


@app.route("/loteria-primera", methods=['GET'])
def search_lotery_primera():
    """Lotería La Primera"""
    search_query = request.args.get('name', "primera")
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("la-primera", search_date, search_query)
    return json_utf8(data)


@app.route("/loteria-primera-12am", methods=['GET'])
def search_lotery_primera_12am():
    """Lotería La Primera 12 AM"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("la-primera/quiniela-medio-dia", search_date, "la primera Día")
    return json_utf8(data)


@app.route("/loteria-primera-noche", methods=['GET'])
def search_lotery_primera_noche():
    """Lotería La Primera Noche"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("la-primera/quiniela-noche", search_date, "Primera Noche")
    return json_utf8(data)


@app.route("/loteria-la-suerte", methods=['GET'])
def search_lotery_la_suerte():
    """Lotería La Suerte"""
    search_query = request.args.get('name', "La Suerte")
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("la-suerte-dominicana", search_date, search_query)
    return json_utf8(data)


@app.route("/loteria-la-suerte-12am", methods=['GET'])
def search_lotery_la_suerte_12am():
    """Lotería La Suerte 12 AM"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("la-suerte-dominicana/quiniela", search_date, "La Suerte 12:30")
    return json_utf8(data)


@app.route("/loteria-la-suerte-tarde", methods=['GET'])
def search_lotery_la_suerte_tarde():
    """Lotería La Suerte Tarde"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("la-suerte-dominicana/quiniela-tarde", search_date, "La Suerte 18:00")
    return json_utf8(data)


@app.route("/loteria-lotedom", methods=['GET'])
def search_lotery_lotedom():
    """Lotería LoteDom"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("lotedom", search_date, "Quiniela LoteDom")
    return json_utf8(data)


@app.route("/loteria-anguila", methods=['GET'])
def search_lotery_anguila():
    """Lotería Anguila"""
    search_query = request.args.get('name', "Anguila")
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("anguila", search_date, search_query)
    return json_utf8(data)


@app.route("/loteria-anguila-10am", methods=['GET'])
def search_lotery_anguila_10am():
    """Lotería Anguila 10 AM"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("anguila/anguila-manana", search_date, "Anguila Mañana")
    return json_utf8(data)


@app.route("/loteria-anguila-12am", methods=['GET'])
def search_lotery_anguila_12am():
    """Lotería Anguila 12 AM"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("anguila/anguila-medio-dia", search_date, "Anguila Medio Día")
    return json_utf8(data)


@app.route("/loteria-anguila-6pm", methods=['GET'])
def search_lotery_anguila_6pm():
    """Lotería Anguila 6 PM"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("anguila/anguila-tarde", search_date, "Anguila Tarde")
    return json_utf8(data)


@app.route("/loteria-anguila-9pm", methods=['GET'])
def search_lotery_anguila_9pm():
    """Lotería Anguila 9 PM"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("anguila/anguila-noche", search_date, "Anguila Noche")
    return json_utf8(data)


@app.route("/loterias-nacionales", methods=['GET'])
def search_lotery_nacionales():
    """Loterías Nacionales"""
    search_query = request.args.get('name', None)
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("loteria-nacional", search_date, search_query)
    return json_utf8(data)


@app.route("/loteria-nacional", methods=['GET'])
def search_lotery_nacional():
    """Lotería Nacional"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("loteria-nacional/quiniela", search_date, "Lotería Nacional")
    return json_utf8(data)


@app.route("/loteria-leidsa", methods=['GET'])
def search_lotery_leidsa():
    """Lotería Leidsa"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("leidsa", search_date, "Quiniela Leidsa")
    return json_utf8(data)


@app.route("/loteria-real", methods=['GET'])
def search_lotery_real():
    """Lotería Real"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("loto-real", search_date, "Quiniela Real")
    return json_utf8(data)


@app.route("/loteria-loteka", methods=['GET'])
def search_lotery_loteka():
    """Lotería Loteka"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("loteka", search_date, "Quiniela Loteka")
    return json_utf8(data)


@app.route("/loteria-americana", methods=['GET'])
def search_lotery_americana():
    """Loterías Americanas"""
    search_query = request.args.get('name', None)
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("americanas", search_date, search_query)
    return json_utf8(data)


@app.route("/loteria-florida-tarde", methods=['GET'])
def search_lotery_florida_tarde():
    """Lotería Florida Tarde"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("americanas/florida-tarde", search_date, "Florida Día")
    return json_utf8(data)


@app.route("/loteria-florida-noche", methods=['GET'])
def search_lotery_florida_noche():
    """Lotería Florida Noche"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("americanas/florida-noche", search_date, "Florida Noche")
    return json_utf8(data)


@app.route("/loteria-new-york-12am", methods=['GET'])
def search_lotery_new_york_12am():
    """Lotería New York 12 AM"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("americanas/new-york-medio-dia", search_date, "New York Tarde")
    return json_utf8(data)


@app.route("/loteria-new-york-noche", methods=['GET'])
def search_lotery_new_york_noche():
    """Lotería New York Noche"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("americanas/new-york-noche", search_date, "New York Noche")
    return json_utf8(data)


@app.route("/loteria-king-lottery-12pm", methods=['GET'])
def search_lotery_king_lottery_12pm():
    """Lotería King Lottery 12 PM"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("king-lottery/quiniela-dia", search_date, "King Lottery 12:30")
    return json_utf8(data)


@app.route("/loteria-king-lottery-7pm", methods=['GET'])
def search_lotery_king_lottery_7pm():
    """Lotería King Lottery 7 PM"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("king-lottery/quiniela-noche", search_date, "King Lottery 7:30")
    return json_utf8(data)


@app.route("/el-quemaito-mayor-12pm", methods=['GET'])
def search_lotery_quemaito():
    """El Quemaito Mayor 12 PM"""
    search_date = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
    data = scrapingByName("el-quemaito-mayor", search_date, "El Quemaito Mayor 12:00")
    return json_utf8(data)


@app.errorhandler(404)
def not_found(error):
    """Manejo de errores 404"""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Manejo de errores 500"""
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=port, debug=False)