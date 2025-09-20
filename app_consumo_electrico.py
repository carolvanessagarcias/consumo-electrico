"""app_consumo_electrico.py
Aplicación web simple con Flask para controlar consumo eléctrico (Colombia).
- Registrar electrodomésticos (nombre, potencia W, horas/día)
- Mostrar resumen con consumo mensual, costo (TARIFA = 700 COP/kWh)
- Advertencias y recomendaciones según consumo
- Guardar y descargar datos en CSV

Instrucciones:
1. Instalar dependencias: pip install flask
2. Ejecutar: python app_consumo_electrico.py
3. Abrir en el navegador: http://127.0.0.1:5000

Archivo único (no templates externos): todo se sirve con render_template_string.
"""
from flask import Flask, request, redirect, url_for, render_template_string, send_file, flash
import csv
import io
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'dev_secret_key'

TARIFA = 700  # COP por kWh

# Datos en memoria: lista de dicts
electrodomesticos = []

BASE_HTML = """
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Control de Consumo Eléctrico</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  </head>
  <body class="bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
      <div class="container-fluid">
        <a class="navbar-brand" href="/">Consumo Eléctrico (COL)</a>
      </div>
    </nav>

    <div class="container">
      {% with messages = get_flashed_messages() %}
        {% if messages %}
          {% for m in messages %}
            <div class="alert alert-info">{{ m }}</div>
          {% endfor %}
        {% endif %}
      {% endwith %}

      <div class="row">
        <div class="col-md-5">
          <div class="card mb-3">
            <div class="card-header">Agregar electrodoméstico</div>
            <div class="card-body">
              <form method="post" action="/add">
                <div class="mb-3">
                  <label class="form-label">Nombre</label>
                  <input class="form-control" name="nombre" required>
                </div>
                <div class="mb-3">
                  <label class="form-label">Potencia (W)</label>
                  <input class="form-control" name="potencia" type="number" step="any" min="0" required>
                </div>
                <div class="mb-3">
                  <label class="form-label">Horas de uso diario</label>
                  <input class="form-control" name="horas" type="number" step="any" min="0" required>
                </div>
                <button class="btn btn-primary" type="submit">Agregar</button>
              </form>
            </div>
          </div>

          <div class="card">
            <div class="card-header">Acciones</div>
            <div class="card-body">
              <a class="btn btn-success mb-2" href="/download">Descargar CSV</a>
              <a class="btn btn-secondary mb-2" href="/clear">Limpiar datos</a>
              <p class="small text-muted mt-2">Tarifa usada: <strong>{{ tarifa }} COP/kWh</strong></p>
            </div>
          </div>
        </div>

        <div class="col-md-7">
          <div class="card">
            <div class="card-header">Resumen de consumo</div>
            <div class="card-body">
              {% if not items %}
                <p>No hay electrodomésticos registrados.</p>
              {% else %}
                <table class="table table-sm">
                  <thead>
                    <tr>
                      <th>Nombre</th>
                      <th>Potencia (W)</th>
                      <th>Horas/día</th>
                      <th>Consumo kWh/mes</th>
                      <th>Costo COP/mes</th>
                      <th>Recomendación</th>
                    </tr>
                  </thead>
                  <tbody>
                    {% for e in items %}
                    <tr>
                      <td>{{ e.nombre }}</td>
                      <td>{{ e.potencia_W }}</td>
                      <td>{{ e.horas_diarias }}</td>
                      <td>{{ '%.2f'|format(e.consumo_mensual_kWh) }}</td>
                      <td>{{ '%.0f'|format(e.costo_pesos) }}</td>
                      <td>
                        {% if e.consumo_mensual_kWh > 50 %}
                          <span class="badge bg-danger">ALERTA</span>
                          <div>Reduce horas, desconéctalo o busca equipo más eficiente.</div>
                        {% elif e.consumo_mensual_kWh > 30 %}
                          <span class="badge bg-warning text-dark">Advertencia</span>
                          <div>Usa menos horas o activa modo ahorro de energía.</div>
                        {% else %}
                          <span class="badge bg-success">OK</span>
                          <div>Desconéctalo cuando no lo uses.</div>
                        {% endif %}
                      </td>
                    </tr>
                    {% endfor %}
                  </tbody>
                </table>

                <hr>
                <p><strong>TOTAL:</strong> {{ '%.2f'|format(total_consumo) }} kWh/mes | <strong>{{ '%.0f'|format(total_costo) }} COP/mes</strong></p>
              {% endif %}
            </div>
          </div>
        </div>
      </div>

      <footer class="mt-4 text-center text-muted">
        Proyecto estudiantil · Tarifa de referencia: {{ tarifa }} COP/kWh
      </footer>
    </div>

  </body>
</html>
"""

@app.route('/')
def index():
    total_c = sum(e['costo_pesos'] for e in electrodomesticos)
    total_kwh = sum(e['consumo_mensual_kWh'] for e in electrodomesticos)
    return render_template_string(BASE_HTML, items=electrodomesticos, total_consumo=total_kwh, total_costo=total_c, tarifa=TARIFA)

@app.route('/add', methods=['POST'])
def add():
    try:
        nombre = request.form['nombre'].strip()
        potencia = float(request.form['potencia'])
        horas = float(request.form['horas'])
        consumo_diario = (potencia * horas) / 1000.0
        consumo_mensual = consumo_diario * 30
        costo = consumo_mensual * TARIFA

        electrodomesticos.append({
            'nombre': nombre,
            'potencia_W': potencia,
            'horas_diarias': horas,
            'consumo_mensual_kWh': consumo_mensual,
            'costo_pesos': costo,
            'timestamp': datetime.now().isoformat()
        })
        flash(f"{nombre} agregado correctamente.")
    except Exception as ex:
        flash(f"Error al agregar: {ex}")
    return redirect(url_for('index'))

@app.route('/download')
def download_csv():
    if not electrodomesticos:
        flash('No hay datos para descargar.')
        return redirect(url_for('index'))

    output = io.StringIO()
    fieldnames = ['nombre','potencia_W','horas_diarias','consumo_mensual_kWh','costo_pesos','timestamp']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for e in electrodomesticos:
        writer.writerow({k: e.get(k, '') for k in fieldnames})

    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    filename = 'consumo_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.csv'
    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name=filename)

@app.route('/clear')
def clear_data():
    electrodomesticos.clear()
    flash('Datos limpiados.')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
