
	Resultados
El apartado de Resultados sigue una estructura común en todos los problemas para mostrar de forma clara cómo trabaja el software. Cada bloque comienza con el enunciado original, seguido de las modificaciones necesarias para su adaptación al modelo computacional. Después se expone la resolución, donde se construyen las curvas características, se determina el punto de funcionamiento y se analizan los parámetros hidráulicos relevantes. Cuando el problema incorpora elementos adicionales, se describe la metodología de las funciones extra implementadas. Finalmente, los resultados y su validación comparan las salidas del programa con las soluciones teóricas, demostrando que el comportamiento obtenido es coherente y que el modelo reproduce correctamente los casos incluidos en IBS.
4.1 Problema nº1: Bombeo entre depósitos con válvula de regulación en la impulsión
4.1.1 Enunciado original del Problema nº1  

  

4.1.2 Modificaciones al enunciado original del Problema nº1
El enunciado original se ha extendido para que el estudiante explore cómo cambian las curvas características y el punto de funcionamiento con la instalación de una válvula de asiento reductora de presión en la tubería de impulsión.
Se añade al enunciado original una válvula reguladora de caudal con apertura ajustable α ∈ [0,100]%. Su efecto se modela como una pérdida adicional que eleva la CCI manteniendo la misma cota piezométrica. Para α = 100% se fuerza 〖hf〗_válvula=0 para que los resultados sean iguales en esa casuística. En cambio, para α = 0% el caudal es nulo en servicio, y salta un aviso.
Esta palanca adicional permite visualizar, en tiempo real, el desplazamiento de las curvas y del punto de funcionamiento, y entender la interacción bomba–sistema–control.
Complementando la inclusión de la válvula, se han realizado las adaptaciones de software necesarias para transformar el problema en un sistema completamente interactivo. El usuario puede manipular parámetros fundamentales de la instalación, como los diámetros de las tuberías, la densidad relativa del fluido, las longitudes de los tramos y el coeficiente de rugosidad absoluta. 
Estas modificaciones se han implementado siguiendo criterios de coherencia técnica y rigor ingenieril, asegurando que la herramienta mantenga su utilidad pedagógica sin permitir escenarios físicamente imposibles. Para ello, se han definido restricciones y rangos lógicos en los controles de entrada. Para ilustrar, la selección de los diámetros de tubería se ha restringido exclusivamente a valores comerciales mediante pasos fijos de 25 mm para garantizar el realismo del modelo frente a la práctica profesional de la ingeniería. 

4.1.3 Resolución del Problema nº1
El desarrollo del software correspondiente al Problema nº1 se ha realizado siguiendo de forma rigurosa la resolución teórica planteada en el enunciado original. Se ha partido de la aplicación directa de la ecuación de Bernoulli entre los depósitos A y B, incorporando las pérdidas de carga calculadas mediante la fórmula de Hazen–Williams. 
En la implementación digital se introdujo una ligera modificación respecto a la resolución original: se añadió un término adicional asociado a una válvula de regulación con pérdida de carga h_f^("v" "a"  ˊ"lvula" ) (Q). Este término, inicialmente nulo, permite al usuario simular distintas condiciones de operación y observar cómo varía la curva característica de la instalación en función de la apertura de la válvula. De este modo, la expresión final adoptada en el software es:
 
Para la representación de la bomba se utilizaron los datos experimentales proporcionados en el problema, definiendo la curva característica mediante interpolación lineal entre los puntos de caudal, altura y rendimiento. El punto de funcionamiento obtenido (Q=42,39 l/s, H=31,04 m, η=76 %) se determinó automáticamente como la intersección entre la curva de la instalación y la de la bomba.
En el desarrollo digital se incorporó la posibilidad de modificar la presión en el depósito B, lo que permite simular la presurización y el correspondiente cambio de punto de funcionamiento. Asimismo, se incluyó una herramienta interactiva para calcular la presión límite del depósito superior que impediría la circulación del fluido, obtenida en torno a 330 kPa, coherente con la altura manométrica máxima de la bomba.
Todas las magnitudes se implementaron en unidades coherentes (m, l/s, mcl) y con precisión decimal controlada para evitar acumulación de errores. Se priorizó la reproducibilidad de resultados, de forma que cualquier variación de diámetro, longitud o rugosidad se refleje de inmediato en las curvas.
A continuación, se muestra la resolución del problema para los datos originales.
Se aplica Bernoulli entre el depósito A y B.
 
Utilizando la fórmula de Hazen-Williams. 
〖hf〗_AB=〖hf〗_1+〖hf〗_2=J_1^(  1)·L_1·Q^1,852+J_1^(  2)·L_2·Q^1,852
Previamente se calculan las pérdidas de carga unitarias J_1^(  1) y J_1^(  2).
=0,01 cm (Cuadro de rugosidades).
 
J_1^(  1)=9,17·10^(-6)
 
J_1^(  2)=3,72·10^(-5)

 
 
Se dibujan tanto la CCI como la CCTB y se saca el punto de funcionamiento y el rendimiento. 
H_m=31mcl,Q=42,5 l/s,η=76%
Luego, la potencia absorbida: 
P_abs=γQH/η=(1,2·9800·42,5·10^(-3)·31)/(0,76·1000)=20,39 kW
Si se presuriza el depósito B a 0,5 kg/cm^2 varía la ordenada en el origen de la cc de la instalación.
  
En el caso de que la cci y la ccb no se corten, es decir no exista un punto de intersección, no podrá circular líquido por la tubería ya que no se le aporta la energía necesaria. Para ello la cci tendrá que desplazarse hacia arriba, paralelamente a sí misma, es decir incrementar la presión en el depósito superior. La mínima ordenada en el origen, viene definida por la ordenada en el origen de la bomba: 38 mcl; como en la instalación z=10m:
P_B/γ≥38-10=28 mcl;P_B=28·1,2·9800=330 kPa
4.1.4 Metodología para las funciones extra del Problema nº1
Para modelar la pérdida en la válvula de impulsión se emplea la relación capacidad relativa  = K_v/K_(v,max)  en función de la apertura α de una válvula globo (plug parabólico, to close). Los valores de  (α) se toman de la Tabla 4.1, que es la tabla de Emerson/Fischer (Catalog 12, Section 1, 2017) y se interpolan linealmente entre puntos.
RELATIVE FLOW COEFFICIENT 
Opening ratio α	0.10	0.20	0.40	0.60	0.80	1.00
Globe, parabolic plug
(Flow direction: To close)	0.20	0.30	0.50	0.60	0.80	1.00
Tabla 4.1. Capacidad relativa Φ en función de la apertura, válvula globo (parabolic plug, to close).
En las Figuras 4.1 y 4.2 cómo evoluciona la curva característica de la instalación (CCI) al ir cerrando la válvula, para aperturas del 70% y del 30%, respectivamente. La CCI base se representa en color azul discontinuo, y los casos con válvula parcial en naranja continuo. 
 

Figura 4.1. Comparación de CCI base (apertura 100 %) y CCI con válvula (apertura 70%).

 

Figura 4.2. Comparación de CCI base (apertura 100 %) y CCI con válvula (apertura 30%).
Para terminar con la válvula de asiento, cuando se cierra al 100 % su capacidad de paso queda prácticamente en cero. Eso equivale a una resistencia hidráulica enorme, lo que implica que no circule caudal. En el diagrama, la CCI se vuelve una línea vertical que no llega a intersectar la curva de la bomba; el único estado posible es Q=0. La cota piezométrica permanece igual (a caudal nulo no hay pérdidas), pero no hay movimiento de fluido. Se presenta en la Figura 4.3 el aviso que salta en el programa en dicha casuística.

 
Figura 4.3. CCI base (apertura 100 %) y CCI vertical con válvula completamente cerrada. Q=0.

4.1.5 Resultados y validación del modelo
A continuación, se presenta una captura de pantalla de la interfaz del problema nº1 (Figura 4.4) que muestra los resultados obtenidos con el programa.
 

Figura 4.4. Interfaz gráfica y resultados numéricos del Problema nº1 con datos originales.
Hay algunas pequeñas diferencias, tales como la potencia absorbida (20,39kW frente a 20,35kW) y el caudal en el punto de funcionamiento (42,5 L/s frente a 42,39 L/s). Estas diferencias se deben al cálculo numérico en coma flotante del programa (uso de valores no redondeados, interpolaciones lineales y conversiones de unidades con mayor precisión). En términos de ingeniería son despreciables y plenamente aceptables, ya que se encuentran dentro del error esperado por redondeo (%2) y no alteran las conclusiones ni el punto de funcionamiento de la instalación.
Con el fin de validar el correcto funcionamiento del software desarrollado, se ha realizado una comparación directa entre los resultados obtenidos numéricamente y los valores teóricos proporcionados en la resolución original del Problema nº1. La Tabla 4.2 recoge los valores de caudal, altura manométrica, rendimiento y potencia absorbida tanto en el caso base como en la situación con el depósito B presurizado, junto con el error relativo entre ambas soluciones.
Esta comparación permite cuantificar el grado de precisión del modelo implementado en Python y confirmar su coherencia con el procedimiento analítico. Los resultados muestran desviaciones mínimas, inferiores al 0,5 %, lo que garantiza la fiabilidad del software para el análisis hidráulico de instalaciones de bombeo simples.
Magnitud	Resultado original	Resultado software	Error (%)
Caudal Q (l/s)	42.5	42.39	0.26 %
Altura H (m)	31.0	31.04	0.13 %
Rendimiento η (%)	76.0	76.0	0.00 %
Potencia absorbida P (kW)	20.39	20.35	0.20 %
Con depósito presurizado Q’ (l/s)	39.0	39.16	0.41 %
Con depósito presurizado H’ (m)	32.4	32.34	0.18 %
Con depósito presurizado η’ (%)	77.2	77.2	0.00 %
Con depósito presurizado P’ (kW)	19.3	19.30	0.00 %
PB límite (kg/cm²)	330	329	0.30 %
Tabla 4.2. Comparación entre los resultados teóricos y los obtenidos mediante el software para el Problema nº1. 
En consecuencia, el modelo computacional no solo reproduce fielmente los resultados analíticos, sino que también facilita su comprensión visual y su análisis paramétrico, contribuyendo a un enfoque didáctico más interactivo de la hidráulica de bombeo.

4.2 Problema nº2: Bombeo de un depósito a un chorro
4.2.1 Enunciado original del Problema nº2

  

4.2.2 Modificaciones al enunciado original del Problema nº2
En este caso, no se ha considerado necesario realizar modificaciones sustanciales sobre el planteamiento original del problema nº2, ya que su formulación resulta suficientemente completa y didáctica. El ejercicio, centrado en el análisis hidráulico de una fuente de chorro vertical impulsada por una bomba centrífuga, permite estudiar de forma clara la interacción entre la curva característica de la instalación y la de la bomba, así como los efectos de las pérdidas por fricción y de la boquilla en la altura alcanzada por el chorro. Este equilibrio entre simplicidad conceptual y riqueza física convierte al problema en un escenario idóneo para una implementación directa en la herramienta didáctica desarrollada.
No obstante, con el objetivo de potenciar su componente visual y facilitar la comprensión del fenómeno, se amplió la interfaz del programa para incluir, además de la representación clásica de las curvas características de la bomba y de la instalación, un componente adicional que muestra el chorro de agua alcanzando su altura real. Este elemento actúa como un complemento visual al análisis hidráulico tradicional, ofreciendo una interpretación más tangible del resultado numérico. Se trata de un añadido propio, concebido como un “plus” para dar mayor visibilidad y atractivo al problema, sin modificar en ningún caso el planteamiento técnico original ni los cálculos establecidos en el enunciado.
En definitiva, la única intervención respecto al enunciado original ha consistido en dotar al problema de un componente visual dinámico, que actúa como puente entre los cálculos teóricos y su interpretación física. La visualización del chorro no solo hace más atractivo el ejercicio, sino que también facilita la enseñanza del concepto de energía disponible y su distribución en una instalación de bombeo. El resultado es un problema que, sin necesidad de alteraciones estructurales, combina rigor académico con una experiencia interactiva más clara y pedagógica.
4.2.3 Resolución del Problema nº2
El desarrollo del software correspondiente al Problema nº2 se ha basado íntegramente en la resolución teórica propuesta en el enunciado original, adaptando las expresiones analíticas y los datos hidráulicos a un entorno interactivo en Python. La formulación de la ecuación de la instalación se mantuvo fiel al modelo de pérdidas por fricción según Hazen–Williams, utilizando el coeficiente C_HW asociado a la rugosidad relativa de la tubería. 
Para la curva característica de la bomba se empleó la familia INP 125/250 – 1450 rpm (Figura 4.5), que permite representar distintos rodetes dentro de la misma carcasa (225, 235, 245, 256 y 266 mm). La curva seleccionada por defecto corresponde al rodete de 256 mm, que es la que se emplea en la resolución original y que define el comportamiento hidráulico de referencia. Esta familia fue incorporada al software a través de un modelo paramétrico obtenido mediante leyes de afinidad, lo que permitió representar de forma realista las variaciones en caudal, altura manométrica y rendimiento al cambiar de rodete.
 
Figura 4.5. Curvas características de las bombas empleadas en el problema nº2
Durante el desarrollo, se priorizó la reproducibilidad de los resultados analíticos. Todas las ecuaciones se implementaron en unidades consistentes, cuidando la coherencia numérica y la interpolación lineal de la curva de bomba. Además, se garantizó la independencia de parámetros, de modo que el usuario puede modificar variables como el diámetro de tubería, la rugosidad o la altura mínima exigida sin que el resto del modelo pierda consistencia.
El apartado visual se concibió como un refuerzo didáctico: además de las curvas características clásicas, se añadió un modelo gráfico del chorro de agua, cuya altura se actualiza en tiempo real según el punto de funcionamiento. Esta funcionalidad, inexistente en el enunciado original, proporciona una interpretación física inmediata de los resultados numéricos y refuerza la comprensión energética del sistema.
A continuación, se muestra la resolución del problema para los datos originales.
Para calcular la expresión analítica de la cci, se aplica Bernoulli entre el depósito de alimentación A y la salida de la boquilla C.

B_A-〖hf〗_tubería+〖Hm〗_i-〖hf〗_boquilla=B_C;  B_C=z_C+(v_c^(  2))/2g
 

Utilizando Hazen-Williams, para calcular las pérdidas de carga en la tubería:
 
La velocidad Vc en la boquilla hay que expresarla en función del caudal en litros/segundo.
 
Sustituyendo los valores en la expresión.

 
b) Hay que seleccionar la bomba para que la altura del chorro sea como mínimo 8 m.

 

Por tanto Q  62, 94 l/s .Dando valores para dibujar la cci.
 

Punto solicitado:
 

Mirando en la curvas de la bomba aportada, la bomba a instalar es la de diámetro de rodete 256 mm.

c) Se toman puntos de la cctb para dibujarla sobre la cci y determinar el punto de funcionamiento

Punto de funcionamiento, P:

Q=66 l/s H=21,8 m =79 %




 
d) La altura del chorro en el punto de funcionamiento será:

 
Si a intervalos se quiere que h=5 m, habrá que disminuir el caudal.

 
Mirando en la ccb, para este caudal la bomba aporta la siguiente altura manométrica:

Hmtb =22 mca

La altura de la instalación, analíticamente, es: 

Hmi = 13,83 mca
 
La diferencia de altura entre la bomba y la instalación para dicho caudal se introduce en pérdida de carga en una válvula.

hfvalvula=22-13,83=8,17 mca
4.2.4 Resultados y validación del modelo
A continuación, se presenta una captura de pantalla de la interfaz del problema nº2 (Figura 4.6) que muestra los resultados obtenidos con el programa para los datos predeterminados. La comparación de resultados se evaluará en el siguiente apartado.

 

Figura 4.6. Interfaz gráfica y resultados numéricos del Problema nº2 con datos originales.
En este caso, a pesar de tener porcentajes de errores superiores a los del problema nº1, el contraste entre los resultados analíticos y los obtenidos mediante el programa confirma nuevamente la precisión del modelo numérico. Las discrepancias observadas en los valores de caudal, altura y potencia se explican por la interpolación de la curva característica y el tratamiento en coma flotante de las magnitudes, lo que introduce nuevamente diferencias inferiores al 2 %.
La Tabla 4.3 recoge los resultados comparativos entre los cálculos teóricos y los obtenidos en el software, tanto para el funcionamiento con altura de chorro de 8 m como para la regulación a 5 m mediante válvula de pérdidas.
Magnitud	Resultado original	Resultado software	Error (%)
Caudal Q (l/s)	66.0	65.97	0.05%
Altura H (m)	21.8	21.88	0.37%
Rendimiento η (%)	79.0	78.4	0.76%
Potencia absorbida P (kW)	17.85	18.04	1.07%
Costo (€/m³)	0.0083	0.0084	1.20%
Altura del chorro h (m)	8.86	8.80	0.68%
Con válvula (h = 5 m) Q’ (l/s)	49.7	49.76	0.12%
hf válvula (mca)	8.17	8.17	0.00%
Tabla 4.3. Comparación entre los resultados teóricos y los obtenidos mediante el software para el Problema nº2. 
Los resultados confirman la total coherencia entre el cálculo teórico y el modelo digital, evidenciando que el software reproduce fielmente el comportamiento hidráulico de la instalación.
4.4 Problema nº4: Fenómeno de la cavitación
4.4.1 Enunciado original del Problema nº4

 

4.4.2 Modificaciones al enunciado original del Problema nº4
Para adaptar el problema teórico a un entorno interactivo y coherente con el funcionamiento real de una instalación, fue necesario introducir varias mejoras respecto al enunciado original. La versión inicial del software permitía modificar parámetros que en la práctica no pueden variarse libremente, lo que generaba combinaciones físicamente imposibles. Estos ajustes iniciales fueron útiles para validar la estructura básica del programa, pero al pasar del papel al entorno dinámico quedó claro que ciertos grados de libertad no eran realistas. Una instalación hidráulica no se comporta como un sistema arbitrario donde cada variable puede moverse sin restricciones; está sujeta a leyes físicas, a condiciones ambientales y a limitaciones propias del equipo.
Durante el desarrollo y en colaboración con la tutora, se comprobó que, si se pretendía que la herramienta fuese didáctica, era indispensable corregir estos aspectos y redefinir varios controles. No se trataba solo de “limitar” al usuario, sino de asegurar que cualquier combinación de valores representase un caso físicamente posible. Estas mejoras no solo resolvieron incoherencias, sino que enriquecieron la experiencia pedagógica, al hacer explícitas dependencias que en un cálculo manual se dan por supuesto. Gracias a ello, la versión final del software no es simplemente una traducción digital del enunciado, sino una representación más fiel y completa del comportamiento real de una instalación hidráulica.
	Sustitución del deslizador de pérdidas de carga por un cálculo físico real

En la primera versión del programa, la pérdida de carga en la aspiración era un deslizador manual. Esto generaba situaciones absurdas, porque la pérdida en la aspiración no puede modificarse “a voluntad”: depende del caudal, del coeficiente de pérdidas k, de la rugosidad, del diámetro en la aspiración y de la longitud equivalente.

Para solucionarlo, la pérdida de carga se recalcula automáticamente 
lo que añade un elemento muy instructivo: el tiempo de uso. A medida que aumenta la antigüedad de la instalación, sube la pérdida de carga debido al ensuciamiento, corrosión y envejecimiento. El software lo muestra de forma inmediata: con más años, la curva naranja sube y el margen de seguridad disminuye.

	La presión atmosférica ya no es un parámetro libre
En el enunciado original, Patm es un dato fijo, pero en la parte interactiva del software se detectó que permitir modificarla manualmente provocaba escenarios imposibles (por ejemplo, una instalación a 2000 metros con 1 bar exacto).

Para evitarlo se añadió un deslizador de altitud de la instalación (z), a partir de la cual la presión atmosférica se calcula automáticamente. Esto ofrece coherencia física y permite estudiar cómo el riesgo de cavitación aumenta a medida que sube la altitud.

	La presión de vapor depende de la temperatura del agua
En la versión manual, Pv era una constante. Esto también generaba situaciones irreales, porque la temperatura influye directamente en la tensión de vapor.
Se añadió un deslizador de temperatura del agua, del que el programa obtiene la presión de vapor Pv(T) mediante interpolación en tabla. El usuario ve de forma inmediata que aumentar T aumenta también P_v/γ, y que por consiguiente reduce el NPSH disponible. 
La Figura 4.7 muestra la diferencia entre la interfaz original y la interfaz final tras la incorporación de estas mejoras. 
 
     
Figura 4.7. Evolución de los parámetros del problema: interfaz inicial (izquierda) y versión final con dependencias físicas implementadas (derecha).
Con estos tres cambios, el problema deja de ser estático y pasa a comportarse como una instalación real donde las condiciones modifican directamente la cavitación.
4.4.3 Resolución del Problema nº4
La resolución del problema sigue el procedimiento estándar para determinar la cota máxima del eje de la bomba evitando cavitación. La metodología aplicada combina tres bloques de cálculo:
	Cálculo del NPSH total exigido por la bomba
El NPSH requerido se obtiene directamente de la gráfica que proporciona el problema nº4. Para cada caudal, el valor debe leerse de dicha curva. En el caso particular del problema, para Q = 28 L/s, la gráfica proporciona NPSH_req ≈ 6,5 mca. A este valor se le suma el margen de seguridad especificado (0,5 m), obteniendo el NPSH mínimo que la instalación debe garantizar. 
Para mantener la fidelidad al problema, la aplicación incorpora directamente dicha curva digitalizada y la representa en pantalla. Sobre esa misma gráfica se superpone la curva NPSH_req + NPSH_seguridad. Es simplemente una curva paralela a la original, pero permite visualizar de manera inmediata el margen disponible y facilita la interpretación de la intersección con el NPSH disponible. Este enfoque resulta mucho más intuitivo y reproduce exactamente la lectura gráfica que exige el método original.

	Obtención del NPSH disponible en la instalación
Se emplea la expresión completa del NPSH disponible, evaluando todos los términos individuales:
	Presión atmosférica convertida a metros de columna,
	presión de vapor del agua a la temperatura indicada,
	pérdida de carga en la aspiración,
	y el desnivel geométrico ΔZ entre la lámina y el eje de la bomba.
El problema se resuelve sustituyendo directamente cada término numérico. En el software se muestra paso a paso la conversión a metros de columna de agua, justo como se ve en la Figura 4.8.

	Igualación de los valores
La metodología consiste en despejar ΔZ a partir de esa igualdad. Una vez calculado el valor, la cota del eje de la bomba se obtiene sumando dicho ΔZ a la cota de la lámina del depósito.
La resolución original presenta exactamente este proceso, desarrollando todas las sustituciones y calculando Z_D = 2000 + 0,675 = 2000,675 m, que es el resultado que toma como referencia nuestra aplicación.
A continuación, se muestra la resolución original del problema.
 
 
 
 
 
 
4.4.4 Metodología para las funciones extra del Problema nº4
Las tres funciones añadidas siguen modelos físicos simplificados pero coherentes con la práctica de cálculo hidráulico.
	Cálculo automático de la presión atmosférica
Se emplea la expresión aproximada utilizada habitualmente en ingeniería para altitudes moderadas (z≤3000 m):
P_atm (z) = 10,33 - z/900 (mca)
Esta relación es suficientemente precisa para el rango de altitudes del problema y reproduce el efecto de la disminución de presión conforme aumenta la altura.
T (ºC)	P_v (mca)
0	0.063
10	0.125
20	0.238
30	0.432
40	0.752
50	1.258
60	2.032
70	3.178
80	4.829
90	7.151
100	10.330
	Cálculo automático de la presión de vapor
Se implementó una tabla Pv(T) basada en valores estándar de la presión de vapor del agua, convertidos directamente a metros de columna de agua para mantener coherencia dimensional en todos los cálculos del NPSH. Estos valores proceden de datos termodinámicos aceptados y permiten trabajar en un rango amplio de temperaturas sin necesidad de recurrir a expresiones empíricas complejas o modelos termodinámicos fuera del alcance didáctico del software. A partir de esta tabla, el programa aplica una interpolación lineal entre puntos consecutivos. La Tabla 4.4 funciona como referencia interna del sistema y actúa como puente entre el valor de temperatura introducido por el usuario y el valor de presión de vapor utilizado en el algoritmo de cálculo del NPSH disponible. Gracias a esta estructura, el deslizador de temperatura puede actualizarse de forma inmediata.

Tabla 4.4. Presión de vapor del agua en función de la temperatura

	Pérdida de carga en aspiración dependiente del uso
Para representar el envejecimiento de la instalación se adoptó la expresión:
h_f  = k · Q² · (1 + 0,01·años)
donde el incremento anual del 1 por ciento simula el ensuciamiento progresivo.
Con esta función, si el usuario incrementa el tiempo de uso, la 〖hf〗_asp crece y el NPSH disponible disminuye, reproduciendo el deterioro típico de las líneas de aspiración.

	Recalculado automático del NPSH disponible
El programa utiliza la ecuación:
〖NPSH〗_disp  = P_atm^(  abs)  - P_v^(  abs)  - 〖hf〗_asp  - Δz
donde Δz depende directamente de z_D. El software muestra la curva obtenida para cada caudal y traza las dos curvas comparativas:
• NPSH requerido + seguridad
• NPSH disponible
La intersección determina la cota necesaria del eje.
Hau aldatu, kurbak ez día hoiek izango.
4.4.5 Resultados y validación del modelo
El programa está configurado inicialmente en el límite exacto de cavitación: con los valores predeterminados, el NPSH disponible coincide prácticamente con el NPSH requerido + margen.
Esto permite visualizar con claridad cómo pequeños cambios afectan a la seguridad:
•Aumentar la temperatura incrementa Pv y reduce el NPSH disponible.
•Aumentar el caudal eleva el NPSH requerido de la bomba.
•Aumentar los años de uso sube hf y reduce el margen.
•Aumentar la altitud z disminuye Patm.
Cuando cualquiera de estos valores mueve el sistema fuera de la zona segura, el software activa automáticamente el aviso de riesgo de cavitación, permitiendo al usuario explorar combinaciones y entender por qué se produce.
A continuación, se presenta una captura de pantalla de la interfaz del problema nº4 (Figura 4.8) que muestra los resultados obtenidos con el programa usando los datos predeterminados.
 

Figura 4.8. Interfaz gráfica y resultados numéricos del Problema nº4 con datos originales.
Aunque a primera vista los dos gráficos parecen prácticamente iguales, en realidad cumplen funciones distintas y representan situaciones hidráulicas diferentes. La coincidencia visual se debe a que ambos muestran las mismas curvas de NPSH requerido y NPSH disponible, pero el modo en que esas curvas se utilizan no es el mismo.
En el Gráfico 1, la altura del eje de la bomba z_D no es un dato fijo, sino una variable que el propio programa ajusta automáticamente hasta encontrar el valor exacto que satisfaga la siguiente condición:
〖NPSH〗_disp= 〖NPSH〗_req  (Q)+〖NPSH〗_seg
Este gráfico sirve para calcular el z_D necesario para el caudal seleccionado. Aquí la curva del NPSH disponible se desplaza verticalmente en función de z_D, y la intersección con la curva del NPSH requerido marca el punto de equilibrio.
En cambio, en el Gráfico 2, la altura z_D ya no cambia: es un valor fijo establecido por el usuario. Con ese z_D invariable, el programa solo recalcula el NPSH disponible cuando se modifican parámetros externos como la altitud o la temperatura del agua. El objetivo de este segundo gráfico es únicamente verificar si, con ese z_D  concreto, la bomba cavitaría o no. Si en el caudal elegido se cumple
〖NPSH〗_disp< 〖NPSH〗_req  (Q)+〖NPSH〗_seg  ,
el fondo se vuelve rojo y aparece el aviso de cavitación (Figura 4.10), dejando claro que la instalación no es segura con ese montaje.

 

Figura 4.9. Gráfico 2 con datos originales, pero con la temperatura del agua a 50ºC.
Por tanto, aunque visualmente ambos gráficos compartan la misma estructura, su función es completamente diferente: el primero calcula la altura necesaria, mientras que el segundo evalúa si la altura fijada es suficiente.
En este problema, la elaboración de una tabla comparativa detallada no resulta especialmente útil. La mayoría de los valores implicados en el cálculo son datos proporcionados directamente por el enunciado, por lo que su coincidencia con el software es automática y no aporta información relevante sobre la fiabilidad del modelo.
Por mantener la coherencia formal con el resto de los problemas, podría presentarse una tabla muy reducida, pero el único valor realmente calculado por el programa y susceptible de comparación es ΔZ y, en consecuencia, la cota final z_D. En ambos casos, el software reproduce el mismo resultado que la resolución analítica, con la única diferencia asociada al redondeo numérico interno.
∆z=0,675 m
z_D=2000,675 m
