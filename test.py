import flet as ft
from google import genai
import sys
import io
import csv
from datetime import datetime
import json
import calendar

# --- FUNCIONES DE GESTIÓN DE DATOS ---

def registrar_en_dataset(texto_usuario, respuesta_json_ia):
    try:
        datos = json.loads(respuesta_json_ia)
        with open('dataset_seguimiento_tca.csv', mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                texto_usuario,
                datos.get('sentimiento'),
                datos.get('ansiedad'),
                datos.get('depresion'),
                datos.get('tca')
            ])
    except Exception as e:
        print(f"Error al guardar en el CSV: {e}")

def obtener_registros_por_fecha(fecha_buscada):
    registros = []
    try:
        with open('dataset_seguimiento_tca.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                fecha_registro = row[0].split(" ")[0] 
                if fecha_registro == fecha_buscada:
                    registros.append({
                        "texto": row[1],
                        "sentimiento": row[2],
                        "tca": row[5]
                    })
    except FileNotFoundError:
        pass
    return registros

# --- CONFIGURACIÓN CLOUD ---
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
client = genai.Client(vertexai=True, project="iron-helper-484014-k8", location="europe-west4")
ENDPOINT_ID = "7290687880945467392"
MODEL_TUNED = f"projects/544705001664/locations/europe-west4/endpoints/{ENDPOINT_ID}"

# --- COMPONENTE CALENDARIO VISUAL ---

def crear_calendario_visual(page, chat_area):
    ahora = datetime.now()
    year, month = ahora.year, ahora.month
    cal = calendar.monthcalendar(year, month)
    
    # Mapeo de estados del mes
    estados_mes = {}
    try:
        with open('dataset_seguimiento_tca.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                f_str = row[0].split(" ")[0]
                dt = datetime.strptime(f_str, "%Y-%m-%d")
                if dt.year == year and dt.month == month:
                    dia = dt.day
                    # Prioridad: si hay un solo TRUE de TCA en el día, se pone ROJO
                    if str(row[5]).lower() == "true":
                        estados_mes[dia] = ft.Colors.RED_900
                    elif dia not in estados_mes:
                        estados_mes[dia] = ft.Colors.BLUE_900
    except FileNotFoundError: pass

    grid = ft.GridView(runs_count=7, max_extent=35, spacing=5, run_spacing=5)
    
    for d in ["L", "M", "X", "J", "V", "S", "D"]:
        grid.controls.append(ft.Text(d, text_align="center", size=10, weight="bold"))

    def dia_click(dia):
        fecha = f"{year}-{month:02d}-{dia:02d}"
        regs = obtener_registros_por_fecha(fecha)
        if not regs: return
        
        lista = ft.Column([ft.Text(f"Registros del {fecha}", weight="bold")])
        for r in regs:
            color = ft.Colors.RED_400 if str(r['tca']).lower() == "true" else ft.Colors.BLUE_400
            lista.controls.append(ft.Text(f"• {r['texto']}", color=color, size=12))
        
        page.dialog = ft.AlertDialog(content=lista)
        page.dialog.open = True
        page.update()

    for semana in cal:
        for dia in semana:
            if dia == 0:
                grid.controls.append(ft.Container())
            else:
                color = estados_mes.get(dia, ft.Colors.GREY_800)
                grid.controls.append(
                    ft.Container(
                        content=ft.Text(str(dia), size=10),
                        bgcolor=color,
                        alignment=ft.Alignment(0, 0),                        
                        border_radius=4,
                        on_click=lambda e, d=dia: dia_click(d)
                    )
                )
    return ft.Container(content=grid, width=280, height=300, padding=10)

# --- MAIN ---

def main(page: ft.Page):
    page.title = "Seguimiento TCA - Historial Visual"
    page.theme_mode = ft.ThemeMode.DARK
    
    chat_area = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    mensaje_bienvenida = (
        "Buenos días. Este es un espacio seguro para ti. "
        "Indica aquí todo lo que haya pasado en tu crisis o cualquier detalle "
        "que quieras que sepa tu psicólogo/a."
    )
    message_input = ft.TextField(hint_text="Escribe aquí...", expand=True)
    sidebar = ft.Column([ft.Text("Historial Mensual", size=16, weight="bold")])
    chat_area.controls.append(
        ft.Row([
            ft.Container(
                content=ft.Text(mensaje_bienvenida, color=ft.Colors.WHITE, selectable=True),
                padding=10, 
                border_radius=10,
                bgcolor=ft.Colors.GREEN_800, # Color diferente para distinguir a la IA
                width=350,
            )
        ], alignment=ft.MainAxisAlignment.START)
    )

    def refrescar_calendario():
        sidebar.controls.clear()
        sidebar.controls.append(ft.Text("Historial Mensual", size=16, weight="bold"))
        sidebar.controls.append(crear_calendario_visual(page, chat_area))
        page.update()

    def create_chat_bubble(text, is_user=True, color=None):
        return ft.Container(
            content=ft.Text(text, color=ft.Colors.WHITE, selectable=True),
            padding=10, border_radius=10,
            bgcolor=color if color else (ft.Colors.BLUE_700 if is_user else ft.Colors.GREY_800),
            width=350,
        )

    def send_click(e):
        user_text = message_input.value
        if not user_text: return
        
        # 1. Limpiar input y bloquearlo
        message_input.value = ""
        message_input.disabled = True
        
        # 2. Añadir mensaje del usuario
        chat_area.controls.append(
            ft.Row([create_chat_bubble(user_text)], alignment=ft.MainAxisAlignment.END)
        )
        
        # 3. Crear el indicador con un color que resalte (Blanco)
        thinking_indicator = ft.Row([
            ft.Container(
                content=ft.Row([
                    ft.ProgressRing(width=16, height=16, stroke_width=2, color=ft.Colors.WHITE),
                    ft.Text(" Analizando crisis...", italic=True, size=12, color=ft.Colors.WHITE)
                ]),
                padding=10,
                border_radius=10,
                bgcolor=ft.Colors.BLACK54,
            )
        ], alignment=ft.MainAxisAlignment.START)
        
        chat_area.controls.append(thinking_indicator)
        
        # --- EL TRUCO PARA QUE APAREZCA ---
        page.update() # Forzamos el dibujo del círculo
        
        try:
            # 4. Llamada al modelo de Vertex AI
            # (El programa se detiene aquí, pero como ya llamamos a update(), el círculo se queda visible)
            prompt = f"Analiza y responde en JSON: 'sentimiento','ansiedad','depresion','tca'. Texto: {user_text}"
            response = client.models.generate_content(model=MODEL_TUNED, contents=prompt)
            res_raw = response.text.strip().replace("```json", "").replace("```", "")
            
            datos = json.loads(res_raw)
            registrar_en_dataset(user_text, res_raw)
            
            # Preparar la burbuja de respuesta
            color = ft.Colors.RED_900 if datos.get('tca') else (ft.Colors.GREEN_700 if datos.get('sentimiento') == "positivo" else ft.Colors.GREY_800)
            resumen = f"TCA: {'⚠️ DETECTADO' if datos.get('tca') else 'No'}\nSentimiento: {datos.get('sentimiento')}"
            
            # 5. Quitar el indicador y poner la respuesta
            chat_area.controls.remove(thinking_indicator)
            chat_area.controls.append(ft.Row([create_chat_bubble(resumen, False, color)]))
            refrescar_calendario()
            
        except Exception as ex:
            if thinking_indicator in chat_area.controls:
                chat_area.controls.remove(thinking_indicator)
            chat_area.controls.append(ft.Text(f"Error: {ex}", color="red"))
        
        message_input.disabled = False
        page.update()

    send_button = ft.Container(
        content=ft.Image(
            src="enviar.svg", 
            width=30, 
            height=30,
            fit="contain"
        ),
        on_click=send_click,
    )

    # Integración del Layout
    refrescar_calendario()
    
    # 1. Definimos la interfaz (Row)
    interfaz_usuario = ft.Row([
        ft.Container(
            sidebar, 
            width=300, 
            bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.BLACK), 
            padding=10
        ),
        ft.VerticalDivider(width=1, color=ft.Colors.WHITE10),
        ft.Column([
            ft.Container(content=chat_area, expand=True, padding=20),
            ft.Container(
                content=ft.Row([message_input, send_button]), 
                padding=10, 
                bgcolor=ft.Colors.with_opacity(0.6, ft.Colors.BLACK)
            )
        ], expand=True)
    ], expand=True)

    # 2. UN SOLO page.add con el Stack que envuelve todo
    page.add(
        ft.Stack([
            # Fondo: usa el nombre exacto de tu archivo (ej: "image_89cd03.jpg")
            ft.Image(
                src="icons/background.png", 
                fit="cover",
                width=page.width, 
                height=page.height,
            ),
            # Capa superior
            interfaz_usuario
        ], expand=True)
    )

if __name__ == "__main__":
    # assets_dir="." le dice a Flet que busque archivos en la carpeta actual
    ft.app(target=main, assets_dir=".")