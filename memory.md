# Memoria del Proyecto: Liquidador de Multas de Policía

Este archivo actúa como el registro persistente de contexto, decisiones técnicas, estado actual y próximos pasos para el desarrollo y modernización del **Liquidador de Multas de Policía**.

---

## 1. Contexto del Proyecto
El **Liquidador de Multas de Policía** es una herramienta especializada utilizada por la Dirección de Rentas y el Centro de Inteligencia Fiscal de la **Alcaldía de Rionegro** para calcular de forma precisa y oficial el valor de las multas de convivencia ciudadana, incluyendo descuentos por pronto pago/programas comunitarios e intereses moratorios calculados de acuerdo con la reglamentación DIAN o tasas no tributarias fijas.

Originalmente desarrollado como una aplicación de escritorio basada en Python (Tkinter) y compilada en un ejecutable (`LiquidadorMultas.exe`), el proyecto está en proceso de **migración completa a una versión web moderna (Single-Page Application)**.

---

## 2. Estructura de la Base de Datos (`liquidador.db`)
El sistema utiliza una base de datos SQLite persistente con las siguientes tablas clave:

- **`usuarios`**: Gestión de usuarios del sistema con roles (`admin`, `liquidador`), estados activos y control de contraseñas seguras (SHA-256) con cambio provisional obligatorio.
- **`parametros_generales`**: Parámetros globales de la liquidación, como días de gracia para el descuento, porcentaje de descuento general, tasa fija de interés no tributaria y permisos para editar manualmente la fecha de liquidación.
- **`valores_unidad`**: Historial de conversión de unidades de valor según el año. Administra `SMMLV` (Salario Mínimo Mensual), `SMDLV` (Salario Mínimo Diario) y `UVB` (Unidad de Valor de Rionegro para vigencias 2023+).
- **`conceptos_multa`**: Tipos de multas y sus métodos asociados:
  - *Generales (Tipos 1 a 4)*: Tarifas fijas en SMDLV/UVB con posibilidad de descuento por curso pedagógico.
  - *Especiales (Eventos, Urbanismo, Visual)*: Multas variables basadas en cantidades de SMMLV o UVB ingresadas manualmente.
  - *Otras Multas*: Montos manuales con tasa histórica.
  - *No Tributarias*: Montos manuales con tasa fija no tributaria.
- **`tasas_interes`**: Tasas de interés anuales históricas organizadas por mes, año y método de interés, permitiendo liquidar la mora exacta acumulada por trimestres conforme a la regulación DIAN.

---

## 3. Lógica Financiera y Reglas de Negocio Clave
1. **Unidades de Medida**:
   - Para vigencias de multa **hasta el año 2022**, la base de cálculo de multas especiales y generales utiliza **SMMLV** y **SMDLV**.
   - A partir del año **2023**, se realiza la transición automática de unidades a **UVB** (Unidad de Valor de Rionegro).
2. **Redondeo Excel**:
   - Todas las bases de liquidación e intereses se redondean al millar más cercano, emulando la fórmula de Excel `REDONDEAR(valor, -3)` (ej: `$12,345` se convierte en `$12,000`).
3. **Cálculo de Descuentos**:
   - Si los días transcurridos entre la fecha de la multa y la liquidación son inferiores o iguales a los días de gracia parametrizados (normalmente 8 días), se aplica descuento.
   - Multas Generales Tipo 1 y 2, y Especiales: 50% de descuento.
   - Multas Generales Tipo 3 y 4: 50% estándar. Si el infractor realizó el programa comunitario pedagógico, el descuento aumenta al **75%**.
4. **Cálculo de Intereses**:
   - *Tasa No Tributaria*: Flat diario calculado en base a una tasa fija anual.
   - *Tasas Históricas DIAN*: Interés trimestral acumulativo. Se calculan los días de mora a partir del día siguiente al vencimiento del periodo de gracia, agrupándolos por trimestre calendario y aplicando la tasa oficial del último mes de dicho trimestre.

---

## 4. Estado de Migración Web (V16 - Mayo 2026)
* **Objetivo**: Crear una aplicación web empresarial auto-alojable con backend Flask y frontend Single Page Application (SPA).
* **Fase Actual**: Plan de Implementación Aprobado e Instalación de Recursos del Proyecto.

### Hitos Completados
- [x] Extracción y análisis completo del código fuente de escritorio (versión v15).
- [x] Copia e integración del directorio completo de Habilidades y Animaciones en `/skills`.
- [x] Creación y estructuración del `memory.md` del proyecto en el workspace.
- [x] Configuración del entorno Node.js / NPM e instalación de la librería `motion` para animaciones premium.
- [x] Clonación y montaje completo del framework de diseño inteligente `nexu-io/open-design` (incluyendo sus `design-systems` y más de 130 carpetas de habilidades en `/skills/open-design`).
- [x] Elaboración de la arquitectura del backend en Flask que reutiliza los modelos y servicios de cálculo existentes.

### Siguientes Pasos
- [ ] Creación del servidor de backend `app_web.py`.
- [ ] Diseño y desarrollo de la interfaz responsiva glassmorphic en `templates/index.html` y `static/css/style.css`.
- [ ] Implementación de la interactividad del cliente SPA y llamadas API con fetch en `static/js/app.js`.
- [ ] Fase de validación en navegador de los flujos de cálculo e interfaces de administración de tasas y parámetros.

---

## 5. Historial de Versiones
- **v15 (Escritorio)**: Lanzamiento final de escritorio con base de datos SQLite local, módulo de administración de usuarios y cambio de claves provisionales.
- **v16 (Web)**: Inicio de la migración completa a versión web responsiva de alto rendimiento.
