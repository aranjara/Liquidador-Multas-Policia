// Error reporter client-side to capture debug info on the backend
window.onerror = function (message, source, lineno, colno, error) {
    fetch('/api/debug/error', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            type: 'error',
            message: message,
            source: source,
            lineno: lineno,
            colno: colno,
            stack: error ? error.stack : null
        })
    }).catch(err => console.error('Failed to log error to backend', err));
    return false;
};

window.onunhandledrejection = function (event) {
    fetch('/api/debug/error', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            type: 'unhandledrejection',
            message: event.reason ? (event.reason.message || String(event.reason)) : 'Unhandled Rejection',
            stack: event.reason ? event.reason.stack : null
        })
    }).catch(err => console.error('Failed to log rejection to backend', err));
};

// Fallbacks autosanables locales para ejecución sin internet/intranet municipal
let animate = async (element, keyframes, options) => {
    if (typeof element === 'string') element = document.querySelectorAll(element);
    const elements = element instanceof NodeList || Array.isArray(element) ? element : [element];
    
    elements.forEach(el => {
        if (!el) return;
        if (keyframes) {
            if (keyframes.opacity !== undefined) {
                const opacityVal = Array.isArray(keyframes.opacity) ? keyframes.opacity[keyframes.opacity.length - 1] : keyframes.opacity;
                el.style.opacity = opacityVal;
            }
            if (keyframes.transform !== undefined) {
                const transformVal = Array.isArray(keyframes.transform) ? keyframes.transform[keyframes.transform.length - 1] : keyframes.transform;
                el.style.transform = transformVal;
            }
            if (keyframes.scale !== undefined) {
                const scaleVal = Array.isArray(keyframes.scale) ? keyframes.scale[keyframes.scale.length - 1] : keyframes.scale;
                el.style.transform = (el.style.transform || '').replace(/scale\([^)]*\)/g, '') + ` scale(${scaleVal})`;
            }
            if (keyframes.y !== undefined) {
                const yVal = Array.isArray(keyframes.y) ? keyframes.y[keyframes.y.length - 1] : keyframes.y;
                el.style.transform = (el.style.transform || '').replace(/translateY\([^)]*\)/g, '') + ` translateY(${typeof yVal === 'number' ? yVal + 'px' : yVal})`;
            }
            if (keyframes.x !== undefined) {
                const xVal = Array.isArray(keyframes.x) ? keyframes.x[keyframes.x.length - 1] : keyframes.x;
                el.style.transform = (el.style.transform || '').replace(/translateX\([^)]*\)/g, '') + ` translateX(${typeof xVal === 'number' ? xVal + 'px' : xVal})`;
            }
        }
    });
    return Promise.resolve();
};

let spring = (config) => {
    // Si stiffness y damping están configurados, determinamos si es una curva rebote (bouncy) o suave (smooth)
    if (config && config.stiffness && config.stiffness > 300) {
        // Para botones (e.g. stiffness: 400, damping: 12)
        return 'cubic-bezier(0.34, 1.56, 0.64, 1)'; // easeOutBack (bouncy premium)
    }
    // Para toasts y otros (e.g. stiffness: 200, damping: 15)
    return 'cubic-bezier(0.22, 1, 0.36, 1)'; // easeOutQuint (desaceleración suave premium)
};

// Intentar cargar la librería Motion del CDN de manera asíncrona y segura
(async () => {
    try {
        const module = await import('https://cdn.jsdelivr.net/npm/motion@12.38.0/+esm');
        animate = module.animate;
        // NO sobreescribir 'spring' con module.spring ya que los generadores de Motion-DOM no son
        // compatibles directamente con el easing nativo de Web Animations API en todos los navegadores.
        console.log('Motion library cargada exitosamente del CDN.');
    } catch (e) {
        console.warn('Fallo al cargar la librería Motion del CDN. Usando fallbacks locales sin conexión.', e);
    }
})();

// --- ESTADO GLOBAL CLIENTE ---
let state = {
    currentUser: null,
    concepts: [],
    params: {},
    units: [],
    rates: [],
    users: [],
    currentTab: 'tab-liquidador'
};

// --- UTILERÍAS Y NOTIFICACIONES TOAST ---
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = 'fa-circle-info';
    if (type === 'success') icon = 'fa-circle-check';
    if (type === 'error') icon = 'fa-triangle-exclamation';
    
    toast.innerHTML = `
        <i class="fa-solid ${icon} toast-icon-${type}"></i>
        <div class="toast-content">${message}</div>
    `;
    
    container.appendChild(toast);
    
    // Animar aparición del Toast
    animate(toast, { transform: ['translateX(120%)', 'translateX(0)'] }, { 
        duration: 0.45,
        easing: spring({ stiffness: 200, damping: 15 })
    });
    
    // Auto-eliminar
    setTimeout(() => {
        animate(toast, { opacity: 0, transform: 'translateY(-15px)' }, { duration: 0.3 }).then(() => {
            toast.remove();
        });
    }, 4500);
}

// Convertir YYYY-MM-DD (input date) a DD-MM-YYYY (API expected)
function formatDateToAPI(dateStr) {
    if (!dateStr) return '';
    const parts = dateStr.split('-');
    if (parts.length !== 3) return dateStr;
    return `${parts[2]}-${parts[1]}-${parts[0]}`;
}

// Formatear moneda en Pesos Colombianos COP
function formatCurrency(val) {
    const num = parseFloat(val);
    if (isNaN(num)) return '$0';
    return new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'COP',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(num);
}

// --- CONTROLADOR DE VISTAS (SPA) ---
function showView(viewId) {
    const views = document.querySelectorAll('.view');
    views.forEach(v => {
        if (v.id === viewId) {
            v.classList.remove('hidden');
            // Animación suave de entrada de la vista con Motion
            animate(v, { opacity: [0, 1], scale: [0.98, 1] }, { duration: 0.4 });
        } else {
            v.classList.add('hidden');
        }
    });
}

function switchTab(tabId) {
    const panes = document.querySelectorAll('.tab-pane');
    const menuItems = document.querySelectorAll('.nav-item');
    
    panes.forEach(pane => {
        if (pane.id === tabId) {
            pane.classList.add('active');
            // Animar el contenido del panel con deslizamiento y fade-in
            animate(pane, { opacity: [0, 1], y: [15, 0] }, { duration: 0.35 });
        } else {
            pane.classList.remove('active');
        }
    });
    
    menuItems.forEach(item => {
        if (item.getAttribute('data-tab') === tabId) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
    
    state.currentTab = tabId;
}

// --- ACTUALIZACIÓN DE CAMPOS DINÁMICOS LIQUIDADOR ---
function handleConceptChange() {
    const conceptSelect = document.getElementById('calc-concept');
    const conceptId = conceptSelect.value;
    const selectedConcept = state.concepts.find(c => c.id == conceptId);
    
    const qtyField = document.getElementById('qty-field');
    const qtyLabel = document.getElementById('qty-label');
    const qtyInput = document.getElementById('calc-qty');
    const manualField = document.getElementById('manual-value-field');
    const manualInput = document.getElementById('calc-manual-value');
    const communityField = document.getElementById('community-field');
    const communityInput = document.getElementById('calc-community');
    
    if (!selectedConcept) return;
    
    // Ocultar todos por defecto
    qtyField.classList.add('hidden');
    manualField.classList.add('hidden');
    communityField.classList.add('hidden');
    
    qtyInput.required = false;
    manualInput.required = false;
    
    const code = selectedConcept.codigo;
    
    if (code.startsWith('ME-')) {
        // Infracciones especiales: requieren ingresar cantidad de SMMLV/UVB
        qtyField.classList.remove('hidden');
        qtyInput.required = true;
        
        if (code === 'ME-EVENTOS') qtyLabel.innerHTML = '<i class="fa-solid fa-calculator"></i> Cantidad de SMMLV/UVB (Vigencia)';
        if (code === 'ME-URBANISMO') qtyLabel.innerHTML = '<i class="fa-solid fa-calculator"></i> Metros Cuadrados / Unidades base';
        if (code === 'ME-VISUAL') qtyLabel.innerHTML = '<i class="fa-solid fa-calculator"></i> Cantidad de Elementos Publicitarios';
        
        animate(qtyField, { opacity: [0, 1], y: [8, 0] }, { duration: 0.25 });
        
    } else if (code === 'OM-001' || code === 'NT-001') {
        // Otras multas o No tributarias: requieren ingresar el valor base manualmente en pesos
        manualField.classList.remove('hidden');
        manualInput.required = true;
        animate(manualField, { opacity: [0, 1], y: [8, 0] }, { duration: 0.25 });
        
    } else if (code === 'MG-3' || code === 'MG-4') {
        // Generales Tipo 3 y 4: permiten descuento por programa comunitario
        communityField.classList.remove('hidden');
        animate(communityField, { opacity: [0, 1], y: [8, 0] }, { duration: 0.25 });
    }
}

// --- CARGA DE DATOS DESDE APIS ---

async function fetchInitialData() {
    try {
        // Conceptos
        const cRes = await fetch('/api/concepts');
        state.concepts = await cRes.json();
        
        // Parámetros
        const pRes = await fetch('/api/parameters');
        state.params = await pRes.json();
        
        renderConceptsDropdown();
        applyParametersConfig();
        
        if (state.currentUser.rol === 'admin') {
            // Unidades
            const uRes = await fetch('/api/units');
            state.units = await uRes.json();
            
            // Tasas
            const rRes = await fetch('/api/rates');
            state.rates = await rRes.json();
            
            // Usuarios
            const usRes = await fetch('/api/users');
            state.users = await usRes.json();
            
            renderUnitsTable();
            renderRatesTable();
            renderUsersTable();
        }
    } catch (err) {
        showToast('Error al cargar la información del sistema: ' + err, 'error');
    }
}

function renderConceptsDropdown() {
    const select = document.getElementById('calc-concept');
    select.innerHTML = '';
    
    state.concepts.forEach(c => {
        const option = document.createElement('option');
        option.value = c.id;
        option.textContent = `[${c.codigo}] ${c.nombre}`;
        select.appendChild(option);
    });
    
    handleConceptChange();
}

function applyParametersConfig() {
    // Rellenar formulario de parámetros
    document.getElementById('param-dias').value = state.params.dias_gracia_descuento || 8;
    document.getElementById('param-porcentaje').value = state.params.porcentaje_descuento || 50.0;
    document.getElementById('param-tasa').value = state.params.tasa_no_tributaria || 12.0;
    document.getElementById('param-permitir-editar').checked = !!state.params.permitir_editar_fecha_liquidacion;
    
    // Configurar permisos de fecha de liquidación en el liquidador
    const calcLiqInput = document.getElementById('calc-fecha-liq');
    if (!state.params.permitir_editar_fecha_liquidacion) {
        calcLiqInput.valueAsDate = new Date();
        calcLiqInput.readOnly = true;
    } else {
        calcLiqInput.readOnly = false;
        calcLiqInput.valueAsDate = new Date();
    }
    
    document.getElementById('calc-fecha-multa').valueAsDate = new Date();
}

function renderUnitsTable() {
    const tbody = document.querySelector('#table-unidades tbody');
    tbody.innerHTML = '';
    
    state.units.sort((a, b) => b.anio - a.anio || a.tipo_unidad.localeCompare(b.tipo_unidad));
    
    state.units.forEach(u => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${u.anio}</strong></td>
            <td><span class="badge badge-primary">${u.tipo_unidad}</span></td>
            <td><strong>${formatCurrency(u.valor)}</strong></td>
            <td><span class="badge badge-success">Activo</span></td>
            <td>
                <div class="table-actions">
                    <button class="btn-icon btn-sm btn-edit-unit" data-id="${u.id}" data-anio="${u.anio}" data-tipo="${u.tipo_unidad}" data-valor="${u.valor}" title="Editar">
                        <i class="fa-solid fa-pen-to-square text-primary"></i>
                    </button>
                    <button class="btn-icon btn-sm btn-delete-unit" data-id="${u.id}" title="Eliminar">
                        <i class="fa-solid fa-trash text-danger"></i>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
    
    bindUnitActions();
}

function renderRatesTable() {
    const tbody = document.querySelector('#table-tasas tbody');
    const selectedMethod = document.getElementById('filter-rate-method').value;
    tbody.innerHTML = '';
    
    // Filtrar por el método seleccionado
    const filtered = state.rates.filter(r => r.metodo_interes === selectedMethod && r.activo !== 0);
    filtered.sort((a, b) => b.anio - a.anio || b.mes - a.mes);
    
    filtered.forEach(r => {
        const tr = document.createElement('tr');
        const tasaMensual = (r.tasa_anual / 12.0).toFixed(4);
        tr.innerHTML = `
            <td>${r.anio}</td>
            <td><strong>Mes ${r.mes}</strong></td>
            <td><span class="text-warning">${r.tasa_anual.toFixed(2)}%</span></td>
            <td>${tasaMensual}% mensual</td>
            <td><span class="badge badge-success">Vigente</span></td>
            <td>
                <div class="table-actions">
                    <button class="btn-icon btn-sm btn-edit-rate" data-id="${r.id}" data-metodo="${r.metodo_interes}" data-anio="${r.anio}" data-mes="${r.mes}" data-tasa="${r.tasa_anual}" title="Editar">
                        <i class="fa-solid fa-pen-to-square text-primary"></i>
                    </button>
                    <button class="btn-icon btn-sm btn-delete-rate" data-id="${r.id}" title="Eliminar">
                        <i class="fa-solid fa-trash text-danger"></i>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
    
    bindRateActions();
}

function renderUsersTable() {
    const tbody = document.querySelector('#table-usuarios tbody');
    tbody.innerHTML = '';
    
    state.users.forEach(u => {
        const tr = document.createElement('tr');
        
        const isSelf = u.id === state.currentUser.id;
        const activeBadge = u.activo 
            ? '<span class="badge badge-success">Activo</span>' 
            : '<span class="badge badge-danger">Inactivo</span>';
        
        const forceBadge = u.debe_cambiar_clave 
            ? '<span class="badge badge-danger">SÍ</span>' 
            : '<span class="badge badge-success">NO</span>';
            
        const toggleBtn = isSelf ? '' : `
            <button class="btn-icon btn-sm btn-toggle-active" data-id="${u.id}" data-activo="${u.activo}" title="${u.activo ? 'Desactivar' : 'Activar'}">
                <i class="fa-solid ${u.activo ? 'fa-user-slash text-danger' : 'fa-user-check text-success'}"></i>
            </button>
        `;
        
        const keyBtn = `
            <button class="btn-icon btn-sm btn-reset-pwd" data-id="${u.id}" title="Resetear Contraseña Provisional">
                <i class="fa-solid fa-key text-warning"></i>
            </button>
        `;
        
        const rolBtn = isSelf ? '' : `
            <button class="btn-icon btn-sm btn-change-role" data-id="${u.id}" data-rol="${u.rol}" title="Cambiar Rol">
                <i class="fa-solid fa-rotate text-secondary"></i>
            </button>
        `;
        
        const editBtn = isSelf ? '' : `
            <button class="btn-icon btn-sm btn-edit-user" data-id="${u.id}" data-nombre="${u.nombre || ''}" data-rol="${u.rol}" data-activo="${u.activo}" title="Editar Usuario">
                <i class="fa-solid fa-pen-to-square text-primary"></i>
            </button>
        `;
        
        const deleteBtn = isSelf ? '' : `
            <button class="btn-icon btn-sm btn-delete-user" data-id="${u.id}" title="Eliminar Usuario">
                <i class="fa-solid fa-trash text-danger"></i>
            </button>
        `;
        
        tr.innerHTML = `
            <td><strong>${u.username}</strong></td>
            <td>${u.nombre || 'Sin nombre'}</td>
            <td><span class="badge ${u.rol === 'admin' ? 'badge-danger' : 'badge-primary'}">${u.rol}</span></td>
            <td><small>${u.ultimo_acceso || 'Nunca'}</small></td>
            <td>${forceBadge}</td>
            <td>${activeBadge}</td>
            <td>
                <div class="table-actions">
                    ${toggleBtn}
                    ${keyBtn}
                    ${rolBtn}
                    ${editBtn}
                    ${deleteBtn}
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
    
    bindUserActions();
    initButtonAnimations();
}

// --- LIQUIDACIÓN ACCIONES ---

async function calculateFine(e) {
    e.preventDefault();
    
    const conceptId = document.getElementById('calc-concept').value;
    const fMulta = formatDateToAPI(document.getElementById('calc-fecha-multa').value);
    const fLiq = formatDateToAPI(document.getElementById('calc-fecha-liq').value);
    const qty = document.getElementById('calc-qty').value;
    const manualVal = document.getElementById('calc-manual-value').value;
    const hasCommunity = document.getElementById('calc-community').checked;
    
    const calcBtn = e.target.querySelector('button[type="submit"]');
    calcBtn.disabled = true;
    calcBtn.querySelector('.btn-text')?.setAttribute('data-text', calcBtn.querySelector('.btn-text').textContent);
    if (calcBtn.querySelector('.btn-text')) calcBtn.querySelector('.btn-text').textContent = 'Calculando...';
    
    try {
        const response = await fetch('/api/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                concept_id: conceptId,
                fecha_multa: fMulta,
                fecha_liquidacion: fLiq,
                cantidad_unidades: qty === "" ? null : qty,
                valor_manual: manualVal === "" ? null : manualVal,
                tiene_programa_comunitario: hasCommunity
            })
        });
        
        const data = await response.json();
        
        if (!data.success) {
            showToast(data.message, 'error');
            return;
        }
        
        // Rellenar valores
        const res = data.result;
        document.getElementById('res-total').textContent = formatCurrency(res.total_pagar);
        document.getElementById('res-concept-title').textContent = res.concept_name;
        document.getElementById('res-base').textContent = formatCurrency(res.valor_base);
        document.getElementById('res-unit-detail').textContent = `${res.cantidad_unidades} (${res.unidad_aplicada}) x ${formatCurrency(res.valor_unidad)}`;
        document.getElementById('res-days').textContent = `${res.dias_mora} días (de ${res.dias_transcurridos} totales)`;
        document.getElementById('res-discount').textContent = `-${formatCurrency(res.valor_descuento)} (${res.porcentaje_descuento}%)`;
        document.getElementById('res-interests').textContent = `+${formatCurrency(res.valor_interes)}`;
        document.getElementById('res-rate').textContent = `${res.tasa_interes_anual.toFixed(2)}% anual (${res.metodo_interes})`;
        document.getElementById('res-rules').textContent = res.regla_aplicada;
        
        // Ocultar placeholder y mostrar contenido de resultados
        document.getElementById('result-placeholder').classList.add('hidden');
        const resultContent = document.getElementById('result-content');
        resultContent.classList.remove('hidden');
        
        // Animar la revelación de resultados
        animate(resultContent, { opacity: [0, 1], y: [15, 0] }, { duration: 0.5 });
        
        showToast('Liquidación financiera computada correctamente.', 'success');
        
    } catch (err) {
        showToast('Fallo en la comunicación con el servidor: ' + err, 'error');
    } finally {
        calcBtn.disabled = false;
        if (calcBtn.querySelector('.btn-text')) {
            calcBtn.querySelector('.btn-text').textContent = 'Liquidar Valor Multa';
        }
    }
}

// --- EVENTOS DE ADMINISTRACIÓN ---

async function saveParameters(e) {
    e.preventDefault();
    const dias = document.getElementById('param-dias').value;
    const porcentaje = document.getElementById('param-porcentaje').value;
    const tasa = document.getElementById('param-tasa').value;
    const permitir = document.getElementById('param-permitir-editar').checked;
    
    try {
        const res = await fetch('/api/parameters', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                dias_gracia_descuento: dias,
                porcentaje_descuento: porcentaje,
                tasa_no_tributaria: tasa,
                permitir_editar_fecha_liquidacion: permitir
            })
        });
        const data = await res.json();
        
        if (data.success) {
            showToast(data.message, 'success');
            // Recargar parámetros frescos
            const pRes = await fetch('/api/parameters');
            state.params = await pRes.json();
            applyParametersConfig();
        } else {
            showToast(data.message, 'error');
        }
    } catch (err) {
        showToast('Error al guardar parámetros: ' + err, 'error');
    }
}

async function saveUnit(e) {
    e.preventDefault();
    const anio = document.getElementById('unit-anio').value;
    const tipo = document.getElementById('unit-tipo').value;
    const valor = document.getElementById('unit-valor').value;
    
    try {
        const res = await fetch('/api/units', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ anio, tipo_unidad: tipo, valor })
        });
        const data = await res.json();
        
        if (data.success) {
            showToast(data.message, 'success');
            document.getElementById('unit-modal').classList.add('hidden');
            e.target.reset();
            
            // Recargar tabla de unidades
            const uRes = await fetch('/api/units');
            state.units = await uRes.json();
            renderUnitsTable();
        } else {
            showToast(data.message, 'error');
        }
    } catch (err) {
        showToast('Error de red al guardar unidad: ' + err, 'error');
    }
}

async function saveRate(e) {
    e.preventDefault();
    const metodo = document.getElementById('rate-metodo').value;
    const anio = document.getElementById('rate-anio').value;
    const mes = document.getElementById('rate-mes').value;
    const tasa = document.getElementById('rate-tasa').value;
    
    try {
        const res = await fetch('/api/rates', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ metodo_interes: metodo, anio, mes, tasa_anual: tasa })
        });
        const data = await res.json();
        
        if (data.success) {
            showToast(data.message, 'success');
            document.getElementById('rate-modal').classList.add('hidden');
            e.target.reset();
            
            // Recargar tabla de tasas
            const rRes = await fetch('/api/rates');
            state.rates = await rRes.json();
            renderRatesTable();
        } else {
            showToast(data.message, 'error');
        }
    } catch (err) {
        showToast('Error de red al guardar tasa de interés: ' + err, 'error');
    }
}

async function saveUser(e) {
    e.preventDefault();
    const username = document.getElementById('user-username').value;
    const nombre = document.getElementById('user-nombre').value;
    const password = document.getElementById('user-password').value;
    const rol = document.getElementById('user-rol').value;
    const forceChange = document.getElementById('user-force-change').checked;
    
    try {
        const res = await fetch('/api/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username,
                nombre,
                password,
                rol,
                debe_cambiar_clave: forceChange
            })
        });
        const data = await res.json();
        
        if (data.success) {
            showToast(data.message, 'success');
            document.getElementById('user-modal').classList.add('hidden');
            e.target.reset();
            
            // Recargar tabla de usuarios
            const usRes = await fetch('/api/users');
            state.users = await usRes.json();
            renderUsersTable();
        } else {
            showToast(data.message, 'error');
        }
    } catch (err) {
        showToast('Error de red al registrar usuario: ' + err, 'error');
    }
}

function bindUserActions() {
    // 1. Alternar Activado
    document.querySelectorAll('.btn-toggle-active').forEach(btn => {
        btn.onclick = async (e) => {
            const id = btn.getAttribute('data-id');
            const currentActive = btn.getAttribute('data-activo') === 'true';
            
            try {
                const res = await fetch('/api/users/toggle', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id, activo: !currentActive })
                });
                const data = await res.json();
                
                if (data.success) {
                    showToast(data.message, 'success');
                    const usRes = await fetch('/api/users');
                    state.users = await usRes.json();
                    renderUsersTable();
                } else {
                    showToast(data.message, 'error');
                }
            } catch (err) {
                showToast('Error al alternar estado del usuario: ' + err, 'error');
            }
        };
    });
    
    // 2. Cambiar Rol
    document.querySelectorAll('.btn-change-role').forEach(btn => {
        btn.onclick = async (e) => {
            const id = btn.getAttribute('data-id');
            const currentRol = btn.getAttribute('data-rol');
            const nextRol = currentRol === 'admin' ? 'liquidador' : 'admin';
            
            if (!confirm(`¿Está seguro de cambiar el rol de este usuario a ${nextRol.toUpperCase()}?`)) return;
            
            try {
                const res = await fetch('/api/users/role', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id, rol: nextRol })
                });
                const data = await res.json();
                
                if (data.success) {
                    showToast(data.message, 'success');
                    const usRes = await fetch('/api/users');
                    state.users = await usRes.json();
                    renderUsersTable();
                } else {
                    showToast(data.message, 'error');
                }
            } catch (err) {
                showToast('Error al cambiar rol del usuario: ' + err, 'error');
            }
        };
    });
    
    // 3. Resetear contraseña provisional
    document.querySelectorAll('.btn-reset-pwd').forEach(btn => {
        btn.onclick = async (e) => {
            const id = btn.getAttribute('data-id');
            const newPwd = prompt('Ingrese la nueva contraseña PROVISIONAL para el usuario (mínimo 6 caracteres):');
            if (newPwd === null) return;
            
            const cleanPwd = newPwd.trim();
            if (cleanPwd.length < 6) {
                showToast('La clave provisional debe tener al menos 6 caracteres.', 'error');
                return;
            }
            
            try {
                const res = await fetch('/api/users/reset-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id, provisional_password: cleanPwd })
                });
                const data = await res.json();
                
                if (data.success) {
                    showToast(data.message, 'success');
                    const usRes = await fetch('/api/users');
                    state.users = await usRes.json();
                    renderUsersTable();
                } else {
                    showToast(data.message, 'error');
                }
            } catch (err) {
                showToast('Error al resetear la clave del usuario: ' + err, 'error');
            }
        };
    });
    
    // 4. Eliminar usuario
    document.querySelectorAll('.btn-delete-user').forEach(btn => {
        btn.onclick = async (e) => {
            const id = btn.getAttribute('data-id');
            if (!confirm('¿Está seguro de eliminar este usuario? Esta acción no se puede deshacer.')) return;
            
            try {
                const res = await fetch(`/api/users/${id}`, {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await res.json();
                
                if (data.success) {
                    showToast(data.message, 'success');
                    const usRes = await fetch('/api/users');
                    state.users = await usRes.json();
                    renderUsersTable();
                } else {
                    showToast(data.message, 'error');
                }
            } catch (err) {
                showToast('Error al eliminar el usuario: ' + err, 'error');
            }
        };
    });
    
    // 5. Editar usuario
    document.querySelectorAll('.btn-edit-user').forEach(btn => {
        btn.onclick = async (e) => {
            const id = btn.getAttribute('data-id');
            const nombre = btn.getAttribute('data-nombre');
            const rol = btn.getAttribute('data-rol');
            const activo = btn.getAttribute('data-activo') === 'true';
            
            const newNombre = prompt('Nombre completo:', nombre);
            if (newNombre === null) return;
            
            const newRol = confirm(`Rol actual: ${rol.toUpperCase()}\n\n¿Desea cambiar el rol a ${rol === 'admin' ? 'LIQUIDADOR' : 'ADMIN'}?`) ? (rol === 'admin' ? 'liquidador' : 'admin') : rol;
            
            try {
                const res = await fetch(`/api/users/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ nombre: newNombre, rol: newRol, activo })
                });
                const data = await res.json();
                
                if (data.success) {
                    showToast(data.message, 'success');
                    const usRes = await fetch('/api/users');
                    state.users = await usRes.json();
                    renderUsersTable();
                } else {
                    showToast(data.message, 'error');
                }
            } catch (err) {
                showToast('Error al editar el usuario: ' + err, 'error');
            }
        };
    });
}

function bindUnitActions() {
    // Editar unidad
    document.querySelectorAll('.btn-edit-unit').forEach(btn => {
        btn.onclick = async (e) => {
            const id = btn.getAttribute('data-id');
            const anio = btn.getAttribute('data-anio');
            const tipo = btn.getAttribute('data-tipo');
            const valor = btn.getAttribute('data-valor');
            
            document.getElementById('unit-anio').value = anio;
            document.getElementById('unit-tipo').value = tipo;
            document.getElementById('unit-valor').value = valor;
            
            const modal = document.getElementById('unit-modal');
            modal.classList.remove('hidden');
            animate(modal, { opacity: [0, 1] }, { duration: 0.25 });
        };
    });
    
    // Eliminar unidad
    document.querySelectorAll('.btn-delete-unit').forEach(btn => {
        btn.onclick = async (e) => {
            const id = btn.getAttribute('data-id');
            if (!confirm('¿Está seguro de eliminar este valor de unidad?')) return;
            
            try {
                const res = await fetch(`/api/units/${id}`, {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await res.json();
                
                if (data.success) {
                    showToast(data.message, 'success');
                    const uRes = await fetch('/api/units');
                    state.units = await uRes.json();
                    renderUnitsTable();
                } else {
                    showToast(data.message, 'error');
                }
            } catch (err) {
                showToast('Error al eliminar el valor de unidad: ' + err, 'error');
            }
        };
    });
}

function bindRateActions() {
    // Editar tasa
    document.querySelectorAll('.btn-edit-rate').forEach(btn => {
        btn.onclick = async (e) => {
            const metodo = btn.getAttribute('data-metodo');
            const anio = btn.getAttribute('data-anio');
            const mes = btn.getAttribute('data-mes');
            const tasa = btn.getAttribute('data-tasa');
            
            document.getElementById('rate-metodo').value = metodo;
            document.getElementById('rate-anio').value = anio;
            document.getElementById('rate-mes').value = mes;
            document.getElementById('rate-tasa').value = tasa;
            
            const modal = document.getElementById('rate-modal');
            modal.classList.remove('hidden');
            animate(modal, { opacity: [0, 1] }, { duration: 0.25 });
        };
    });
    
    // Eliminar tasa
    document.querySelectorAll('.btn-delete-rate').forEach(btn => {
        btn.onclick = async (e) => {
            const id = btn.getAttribute('data-id');
            if (!confirm('¿Está seguro de eliminar esta tasa de interés?')) return;
            
            try {
                const res = await fetch(`/api/rates/${id}`, {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await res.json();
                
                if (data.success) {
                    showToast(data.message, 'success');
                    const rRes = await fetch('/api/rates');
                    state.rates = await rRes.json();
                    renderRatesTable();
                } else {
                    showToast(data.message, 'error');
                }
            } catch (err) {
                showToast('Error al eliminar la tasa de interés: ' + err, 'error');
            }
        };
    });
}

// --- AUTENTICACIÓN: LOGIN / LOGOUT / CLAVE ---

async function handleLogin(e) {
    e.preventDefault();
    const userInp = document.getElementById('username').value.trim();
    const pwdInp = document.getElementById('password').value.trim();
    const errAlert = document.getElementById('login-error');
    
    errAlert.classList.add('hidden');
    
    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: userInp, password: pwdInp })
        });
        
        const data = await res.json();
        
        if (!data.success) {
            document.getElementById('login-error-msg').textContent = data.message;
            errAlert.classList.remove('hidden');
            animate(errAlert, { x: [-10, 10, -5, 5, 0] }, { duration: 0.4 });
            return;
        }
        
        state.currentUser = data.user;
        renderHeaderProfile();
        
        // Manejar cambio obligatorio de contraseña inmediatamente
        if (state.currentUser.debe_cambiar_clave === 1) {
            showForcedChangePasswordModal();
            return;
        }
        
        // Ingreso normal
        showToast(`Bienvenido de nuevo, ${state.currentUser.nombre || state.currentUser.username}.`, 'success');
        showView('dashboard-view');
        
        // Cargar todos los datos
        await fetchInitialData();
        
    } catch (err) {
        showToast('Fallo en la comunicación de login: ' + err, 'error');
    }
}

async function handleLogout() {
    if (!confirm('¿Desea cerrar su sesión en el liquidador?')) return;
    
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
        state.currentUser = null;
        showView('login-view');
        document.getElementById('login-form').reset();
        showToast('Sesión cerrada correctamente.', 'info');
    } catch (err) {
        showToast('Error al cerrar sesión: ' + err, 'error');
    }
}

function renderHeaderProfile() {
    const nameEl = document.getElementById('profile-name');
    const roleEl = document.getElementById('profile-role');
    
    nameEl.textContent = state.currentUser.nombre || state.currentUser.username;
    roleEl.textContent = state.currentUser.rol.toUpperCase();
    
    // Revelar u ocultar menús administrativos según rol
    const adminItems = document.querySelectorAll('.admin-only');
    adminItems.forEach(item => {
        if (state.currentUser.rol === 'admin') {
            item.classList.remove('hidden');
        } else {
            item.classList.add('hidden');
        }
    });
}

function showForcedChangePasswordModal() {
    const modal = document.getElementById('pwd-modal');
    const alertBox = document.getElementById('force-pwd-alert');
    const closeBtn = document.getElementById('btn-close-pwd-modal');
    
    alertBox.classList.remove('hidden');
    closeBtn.classList.add('hidden'); // Ocultar botón de cerrar, forzar el cambio
    
    modal.classList.remove('hidden');
    animate(modal, { opacity: [0, 1] }, { duration: 0.3 });
}

async function handleChangePassword(e) {
    e.preventDefault();
    const oldVal = document.getElementById('pwd-old').value.trim();
    const newVal = document.getElementById('pwd-new').value.trim();
    const confVal = document.getElementById('pwd-confirm').value.trim();
    
    if (newVal.length < 6) {
        showToast('La nueva contraseña debe tener al menos 6 caracteres.', 'error');
        return;
    }
    
    if (newVal !== confVal) {
        showToast('La confirmación de la contraseña no coincide.', 'error');
        return;
    }
    
    try {
        const res = await fetch('/api/auth/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                old_password: oldVal,
                new_password: newVal,
                confirm_password: confVal
            })
        });
        
        const data = await res.json();
        
        if (data.success) {
            showToast(data.message, 'success');
            document.getElementById('pwd-modal').classList.add('hidden');
            document.getElementById('pwd-form').reset();
            
            // Si estaba forzado, terminar el proceso de login e ingresar al dashboard
            if (state.currentUser.debe_cambiar_clave === 1) {
                state.currentUser.debe_cambiar_clave = 0;
                showToast('Ingreso completado al dashboard.', 'success');
                showView('dashboard-view');
                await fetchInitialData();
            }
        } else {
            showToast(data.message, 'error');
        }
    } catch (err) {
        showToast('Error al intentar cambiar clave: ' + err, 'error');
    }
}

// --- VERIFICACIÓN DE SESIÓN AUTOMÁTICA EN INICIO ---

async function checkSession() {
    try {
        const res = await fetch('/api/auth/me');
        if (res.status === 401) {
            showView('login-view');
            return;
        }
        
        const data = await res.json();
        if (data.logged_in) {
            state.currentUser = data.user;
            renderHeaderProfile();
            
            if (state.currentUser.debe_cambiar_clave === 1) {
                showView('login-view');
                showForcedChangePasswordModal();
                return;
            }
            
            showView('dashboard-view');
            await fetchInitialData();
            showToast(`Bienvenido de nuevo, ${state.currentUser.nombre || state.currentUser.username}.`, 'success');
        } else {
            showView('login-view');
        }
    } catch (err) {
        showView('login-view');
    }
}

// --- BINDING GENERAL DE EVENTOS DOM ---

const initApp = () => {
    // 1. Verificación inicial de sesión
    checkSession();
    
    // 2. Formularios Auth
    document.getElementById('login-form').onsubmit = handleLogin;
    document.getElementById('logout-btn').onclick = handleLogout;
    document.getElementById('pwd-form').onsubmit = handleChangePassword;
    
    // Ocultar / Mostrar clave
    const toggleBtn = document.getElementById('toggle-pwd-btn');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const pwdInput = document.getElementById('password');
            const icon = toggleBtn.querySelector('i');
            if (pwdInput && icon) {
                if (pwdInput.type === 'password') {
                    pwdInput.type = 'text';
                    icon.className = 'fa-regular fa-eye-slash';
                } else {
                    pwdInput.type = 'password';
                    icon.className = 'fa-regular fa-eye';
                }
            }
        });
    }
    
    // Modals Trigger/Close para Cambio de Clave Normal
    document.getElementById('open-change-pwd-btn').onclick = () => {
        const modal = document.getElementById('pwd-modal');
        document.getElementById('force-pwd-alert').classList.add('hidden');
        document.getElementById('btn-close-pwd-modal').classList.remove('hidden');
        modal.classList.remove('hidden');
        animate(modal, { opacity: [0, 1] }, { duration: 0.3 });
    };
    
    document.getElementById('btn-close-pwd-modal').onclick = () => {
        document.getElementById('pwd-modal').classList.add('hidden');
    };
    
    // 3. Tablas e Interactividad Pestañas
    document.querySelectorAll('.nav-menu button').forEach(btn => {
        btn.onclick = () => {
            const tabId = btn.getAttribute('data-tab');
            switchTab(tabId);
        };
    });
    
    // 4. Cambios Dinámicos en Concepto de Multa
    document.getElementById('calc-concept').onchange = handleConceptChange;
    
    // 5. Submit Formulario de Cálculo
    document.getElementById('liquidador-form').onsubmit = calculateFine;
    
    // 6. Formularios Administrativos y Modals
    document.getElementById('parameters-form').onsubmit = saveParameters;
    document.getElementById('unit-form').onsubmit = saveUnit;
    document.getElementById('rate-form').onsubmit = saveRate;
    document.getElementById('user-form').onsubmit = saveUser;
    
    // Filtrador de Tasas por Categoría
    document.getElementById('filter-rate-method').onchange = renderRatesTable;
    
    // triggers de Modals
    document.getElementById('btn-open-unit-modal').onclick = () => {
        const modal = document.getElementById('unit-modal');
        modal.classList.remove('hidden');
        document.getElementById('unit-anio').value = new Date().getFullYear();
        animate(modal, { opacity: [0, 1] }, { duration: 0.25 });
    };
    
    document.getElementById('btn-close-unit-modal').onclick = () => {
        document.getElementById('unit-modal').classList.add('hidden');
    };
    
    document.getElementById('btn-open-rate-modal').onclick = () => {
        const modal = document.getElementById('rate-modal');
        modal.classList.remove('hidden');
        document.getElementById('rate-anio').value = new Date().getFullYear();
        document.getElementById('rate-mes').value = new Date().getMonth() + 1;
        animate(modal, { opacity: [0, 1] }, { duration: 0.25 });
    };
    
    document.getElementById('btn-close-rate-modal').onclick = () => {
        document.getElementById('rate-modal').classList.add('hidden');
    };
    
    document.getElementById('btn-open-user-modal').onclick = () => {
        const modal = document.getElementById('user-modal');
        modal.classList.remove('hidden');
        animate(modal, { opacity: [0, 1] }, { duration: 0.25 });
    };
    
    document.getElementById('btn-close-user-modal').onclick = () => {
        document.getElementById('user-modal').classList.add('hidden');
    };
    
    // Inicializar animaciones de botones por primera vez
    initButtonAnimations();
    
    // Enlazar de forma segura nuevas animaciones al hacer clicks en la UI (pestañas, modales, etc)
    document.addEventListener('click', () => {
        setTimeout(initButtonAnimations, 50);
    });
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}

// --- ANIMACIONES INTERACTIVAS DE BOTONES CON MOTION (FISICA DE RESORTES) ---
function initButtonAnimations() {
    const buttons = document.querySelectorAll('button, .btn, .btn-icon, .nav-item, .btn-close-modal');
    
    buttons.forEach(btn => {
        if (btn.dataset.animatedBinded) return;
        btn.dataset.animatedBinded = "true";
        
        // Efecto hover: elevar y agrandar ligeramente
        btn.addEventListener('mouseenter', () => {
            animate(btn, { scale: 1.05, y: -2 }, { 
                duration: 0.2, 
                easing: spring({ stiffness: 400, damping: 12 })
            });
        });
        
        // Efecto hover out: retornar a posición de reposo
        btn.addEventListener('mouseleave', () => {
            animate(btn, { scale: 1, y: 0 }, { 
                duration: 0.2, 
                easing: spring({ stiffness: 400, damping: 12 })
            });
        });
        
        // Efecto active click: hundir ligeramente al presionar
        btn.addEventListener('mousedown', () => {
            animate(btn, { scale: 0.94, y: 0 }, { duration: 0.08 });
        });
        
        btn.addEventListener('mouseup', () => {
            animate(btn, { scale: 1.05, y: -2 }, { duration: 0.08 });
        });
    });
}
