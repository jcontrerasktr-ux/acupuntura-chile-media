# Contenido semanal de Instagram: AcupunturaChile

Cuenta: @acupunturachilee. Conector Windsor `instagram`, cuenta `17841406761224388`.
Sitio: acupuntura-chile.cl. Sedes: Santiago, Viña del Mar, La Serena, Talca, Curicó. Servicios: acupuntura, medicina china, kinesiología, masaje terapéutico, osteopatía, quiropraxia, auriculoterapia, programas de bienestar para empresas.
Público: adultos de 25 a 60 años en Chile con dolores crónicos (cabeza, espalda, cuello), estrés, sueño, ansiedad y control de peso; también equipos de empresas.

## Cadencia
- 1 Reel por semana (miércoles, tarde).
- 1 carrusel por semana (lunes, tarde; decisión de Julio, 8 nov 2026). Se suma al Reel y a las 5 historias. Alterna semana a semana: guía para guardar (checklists, hábitos, pausas, preguntas frecuentes) y dato educativo (medicina china, kinesiología, quiropraxia, historia). 5 a 8 láminas de 1080x1350 (4:5), con la guía y la última lámina de cierre con aviso prudente, web y "Guarda y comparte". Herramienta: `python3 tools/make_carrusel.py spec.json media/AAAA-MM-DD-slug/` (modelo: `media/2026-11-09-pausas-trabajo/spec.json`). Publicar con Windsor: acción `create_carousel_post` con `image_urls` (las URLs raw de GitHub, en orden) y `caption` (formato del caption del Reel: gancho con pregunta, idea prudente, "Cada persona responde distinto…", sedes, "Agenda tu hora…", máximo 5 hashtags, invitación a guardar y compartir). Guardar el texto en `caption.txt`. El carrusel NO lleva puntos de acupuntura tampoco. Antes de armar cada carrusel leer `plan/analisis-redes.md` (análisis de redes del 8 nov 2026): 8 o 9 láminas, portada con número o dato en menos de 10 palabras, 2 a 3 láminas de datos con fuente (tipo `dato` de `make_carrusel.py`), una sola invitación final ("Guárdalo y envíaselo a…"), palabras clave en las dos primeras frases y fuentes citadas en el texto.
- 5 historias por semana (desde el 8 de noviembre de 2026), una por día. TODAS son videos animados de 30 a 45 segundos (decisión de Julio, 8 nov 2026), con voz, subtítulos palabra por palabra y la guía de AcupunturaChile. Tipos por día:
  - Lunes: servicios, sedes o empresas. En semana de fecha especial, cuenta regresiva o mensaje de la fecha.
  - Martes: mito o verdad (escenas `tarjeta` con `"chip": "MITO"` y luego `"chip": "VERDAD"`).
  - Jueves: tip práctico de hábitos y bienestar.
  - Sábado: pregunta de la semana para responder por mensaje directo (cerrar la narración invitando a responder).
  - Domingo: dato histórico o de bienestar de la medicina china, o tip suave de descanso y rutina.
- Las historias NO llevan puntos de acupuntura (decisión de Julio, 8 nov 2026). Herramienta: `python3 tools/make_reel_ilustrado.py spec.json media/.../historia.mp4 media/.../portada.jpg` (ejemplo: `media/2026-11-08-neijing-historia/spec.json`). Ilustraciones disponibles: `tarjeta` (ícono de marca `"icono"`: leaf, moon, body, head, wave, curve; `"chip"` opcional), `pergamino` (con `"rotulo"` opcional para mostrar un dato en pantalla), `yinyang` (cinco elementos), `meridianos`, `columna`, `movimiento` y `cierre` (siempre la última escena). Cada escena puede llevar `"guia": "saluda"` o `"quieta"` (personaje propio). Duración total entre 30 y 45 s: unas 6 a 8 escenas con 10 a 16 palabras de narración cada una; `"voz_velocidad": 0.95` si hace falta. El tag, el gancho y `"cierre_texto": "Guarda y comparte esta historia"` van en el spec.
- IMPORTANTE (tiempo): generar un video de 45 s tarda unos 8 minutos y un comando de Bash corta a los 10. Lanzarlo en segundo plano (`nohup python3 tools/make_reel_ilustrado.py ... > gen.log 2>&1 &`) y revisar el log cada 60 s con `sleep 60` hasta ver "ok". Antes: `pip install --break-system-packages -r tools/requirements.txt`. Para publicar: `create_story` con `video_url` (primero URL de GitHub Pages, y si falla sin publicar, una sola vez la raw; ver paso 7).
- Referencia de estilo que mostró Julio: cuenta de medicina china con personaje guía, subtítulos que resaltan la palabra y brillos; solo inspiración, nunca copiar sus dibujos, personaje, textos ni videos. Datos históricos: solo hechos verificados en una fuente y sin promesas (ej.: el Huangdi Neijing, compilado entre el siglo IV a. C. y el III d. C., dos textos de 81 capítulos cada uno: Suwen y Lingshu). Temas: de `plan/temas.json`; con 5 historias a la semana se agotan rápido, así que se puede retomar un tema con otro ángulo y otro texto (nunca repetir el mismo texto); revisar `plan/historial.json` antes.

## Reglas de contenido (obligatorias)
1. Contenido original. Las tendencias que se investigan en la web sirven solo de inspiración para formatos y ganchos. Nunca copiar videos, textos ni imágenes de otras cuentas.
2. Educativo y prudente. No prometer curas ni resultados. No usar porcentajes ni cifras de efectividad. No usar "antes y después". No diagnosticar. Usar fórmulas como "puede ayudar", "como apoyo", "complementario". Si el tema es un síntoma, recordar que ante síntomas intensos o nuevos hay que consultar a un profesional de salud.
3. Nada de pacientes: sin nombres, rostros ni testimonios, salvo que Julio los entregue en el chat y confirme la autorización de la paciente.
4. Español de Chile, trato de tú, tono cercano y simple. Frases cortas.
5. Marca: azul del logo (#395D77) y blanco, amarillo de acento, tipografía Poppins. Todas las historias llevan el logo de AcupunturaChile arriba (`assets/logo_blanco.png`, lo pone `tools/make_story.py` solo) y el Reel lo muestra en el cierre. Siempre mostrar acupuntura-chile.cl. No inventar ni redibujar el logo: usar solo el archivo de `assets/`.
6. No repetir temas: revisar `plan/historial.json` y elegir el siguiente de `plan/temas.json` que no se haya usado (rotar pilares).

## Flujo de una publicación
1. Elegir tema (regla 6) y formato desde `plan/ideas.md`. Para el Reel, hacer una búsqueda web rápida para inspirar el gancho. Revisar las fechas especiales de ese archivo.
2. Escribir el spec JSON (ver docstring de `tools/make_reel.py` y `tools/make_story.py`). Límites: gancho de 12 palabras o menos; título de punto de 6 palabras o menos; cuerpo de 22 palabras o menos; 3 puntos por Reel.
3. Generar en `media/AAAA-MM-DD-slug/`:
   - Antes del primer Reel de la sesión: `pip install --break-system-packages -r tools/requirements.txt` (la voz descarga sola ~350 MB desde GitHub).
   - Reel: `python3 tools/make_reel.py spec.json media/.../reel.mp4 media/.../portada.jpg`
   - Historia: `python3 tools/make_story.py spec.json media/.../historia.jpg`
4. Revisar visualmente (extraer cuadros con ffmpeg y mirarlos): texto sin cortes, sin errores de ortografía, dentro de la zona segura.
5. `git add`, commit y `git push origin HEAD:main`.
6. Comprobar que el archivo existe en GitHub (desde esta sesión solo se alcanza raw, no github.io):
   `curl -sI https://raw.githubusercontent.com/jcontrerasktr-ux/acupuntura-chile-media/main/media/AAAA-MM-DD-slug/reel.mp4` debe dar 200 (reintentar hasta 3 minutos).
7. Publicar con Windsor (cargar las herramientas con ToolSearch: `select:mcp__Windsor_ai__execute_action,mcp__Windsor_ai__list_actions`). Julio ya activó GitHub Pages: tras el push, esperar 2 minutos y usar primero la URL de Pages `https://jcontrerasktr-ux.github.io/acupuntura-chile-media/media/AAAA-MM-DD-slug/reel.mp4` (entrega el tipo `video/mp4` que Instagram exige; no se puede verificar desde esta sesión). Si Windsor devuelve un error de URL o formato y NO publicó, reintentar una sola vez con la URL raw de `raw.githubusercontent.com` (verificada en el paso 6). Si ambas fallan, no publicar y avisar a Julio. Para historias (imágenes) sirve cualquiera de las dos.
   - Reel: acción `create_video_post` con `video_url`, `caption`, `cover_url` (portada.jpg) y `share_to_feed: true`.
   - Historia: acción `create_story` con `image_url`.
8. Registrar en `plan/historial.json` (fecha, tipo, id_tema, resultado), commit y push.
9. Enviar a Julio un resumen corto con `SendUserMessage`: qué se publicó, el texto y el resultado. Si algo falla, explicarlo y no reintentar más de una vez.

## Reel ilustrado (educativo, alterna con el de puntos)
- Formato: dibujos animados propios + subtítulo palabra por palabra + voz. Herramienta: `python3 tools/make_reel_ilustrado.py spec.json reel.mp4 portada.jpg` (ejemplo en `plan/ejemplos/ilustrado-columna.json`; ilustraciones: columna, movimiento, meridianos, cierre).
- Contenido desde las tres miradas de la clínica: medicina china, kinesiología y quiropraxia. No hace falta que cada Reel hable de todas: la mayoría se centra en UNA terapia (rotar entre ellas) y de vez en cuando uno junta las tres, como el ejemplo. Explicar con datos de anatomía o conceptos de la tradición ("según la medicina china…"), sin cifras de efectividad ni promesas.
- Reels de PUNTOS DE ACUPUNTURA para una molestia (tensión de cabeza, estrés, sueño, digestión): ilustración `punto` con `zona` cara|mano|pierna|oreja (ejemplo: `plan/ejemplos/ilustrado-puntos-cabeza.json`). Mostrar nombre y ubicación del punto, decir que se usa "en medicina china como apoyo", masaje suave y sin dolor, sin cifras ni promesas, y cerrar recordando que no reemplaza una evaluación y que ante dolor intenso o nuevo hay que consultar. Puntos disponibles: Yintang y Taiyang (cara), Hegu (mano), Zusanli (pierna), Shenmen (oreja).
- Alternar: semana con Reel de puntos (`make_reel.py`) y semana con Reel ilustrado. Julio debe aprobar el primero antes de publicarlo.
- Estilo de dibujo aprobado por Julio (volumen, sombras, tonos de piel, detalles): no cambiarlo. Cualquier ilustración nueva debe seguir el mismo estilo.
- Inspiración: formatos de otras cuentas (ilustración animada, subtítulos que resaltan la palabra). Jamás copiar sus dibujos, textos ni videos.

## Voz del Reel
- Julio eligió voz sintética en español neutro (no chileno). Todos los Reels llevan `"voz": true` y `"voz_id": 28` (mujer) en el spec; la narración lee gancho, puntos y cierre (`narracion()` en `tools/make_reel.py`).
- Si Julio envía su propia grabación, usarla en vez de la sintética.

## Portada del Reel
- `make_reel.py` genera la portada sola: azul liso del logo (#395D77), logo arriba, etiqueta, gancho en blanco con acento amarillo y acupuntura-chile.cl. Todo queda en la franja central que recorta la grilla del perfil. No cambiar a otro estilo.

## Formato del texto del Reel (caption)
- Primera línea: gancho con una pregunta. Segundo párrafo: idea central en 1 o 2 frases prudentes. Tercer párrafo: "Cada persona responde distinto; en AcupunturaChile evaluamos tu caso y armamos un plan a tu medida."
- Luego: sedes y "Agenda tu hora: acupuntura-chile.cl (link en bio)".
- Hashtags: máximo 5 (límite de Instagram): #acupuntura #AcupunturaChile más 3 relevantes del tema. Cerrar con una invitación a guardar o compartir y, si calza, una pregunta para comentar.

## Videos propios de Julio
Cuando Julio envía un video en el chat, se edita con corte de silencios, mejora de voz, subtítulos y portada, se sube a `media/` y se publica con el mismo flujo, siempre que confirme la autorización de las personas que aparecen.

## Contenido ya preparado y mostrado a Julio
- **Reel ilustrado del miércoles 18 de noviembre de 2026:** aprobado por Julio y generado en `media/2026-11-18-columna-tres-miradas/` (`reel.mp4`, `portada.jpg`, `caption.txt`). En esa ejecución NO generar otro: publicar exactamente ese Reel (pasos 6 a 9). Desde el 25 de noviembre, alternar formato y centrar cada Reel ilustrado en una sola terapia.
- **Reel del miércoles 11 de noviembre de 2026:** ya está generado en `media/2026-11-11-primera-sesion/` (`reel.mp4` con voz neutra ya incluida, `portada.jpg`, `caption.txt`, tema `primera-sesion`). En esa ejecución NO generar otro: comprobar la URL, publicar exactamente ese Reel con ese texto (pasos 6 a 9) y registrarlo en el historial. Si Julio pidió cambios antes, estarán reflejados en esa carpeta.
- **Carrusel del lunes 9 de noviembre de 2026:** ya está generado en `media/2026-11-09-pausas-trabajo/` (`lamina-01.jpg` a `lamina-09.jpg`, `caption.txt`; dato sobre dolor de espalda y guía "5 pausas de 1 minuto para tu jornada"). En esa ejecución NO generar otro: comprobar las URLs raw y publicar exactamente esas 9 láminas con ese texto (`create_carousel_post`), registrar en el historial (tipo carrusel, id_tema `pausas-trabajo`). El carrusel del 16 de noviembre de 2026 ya está generado en `media/2026-11-16-migrana/` (`lamina-01.jpg` a `lamina-09.jpg`, `caption.txt`; dato sobre migraña con cifras GBD 2021 y guía de 4 hábitos, pedido por Julio el 9 nov tras el análisis de redes). En esa ejecución NO generar otro: comprobar las URLs raw y publicar exactamente esas 9 láminas con ese texto (`create_carousel_post`), registrar en el historial (tipo carrusel, id_tema `migrana-habitos`).
