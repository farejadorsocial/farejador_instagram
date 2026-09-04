# Organização do frontend

- `js/app.js`: ponto de entrada compatível com a URL antiga.
- `js/core/runtime.js`: estado, utilitários e inicialização.
- `js/modules/`: blocos funcionais extraídos do `app.js` original, sem reescrever a lógica.
- `css/style.css`: ponto de entrada compatível.
- `css/modules/`: estilos separados por seções que já existiam no CSS original.

A ordem de carregamento dos módulos JS é intencional: os módulos compartilham o mesmo estado global legado.
