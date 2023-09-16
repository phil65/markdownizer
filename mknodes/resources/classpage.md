{% if cls.__subclasses__() %}
### Sub classes
{{ cls.__subclasses__() | MkClassTable }}
{% endif %}

{% if cls.mro() | length > 2 %}
### Base classes
{{ cls.__bases__ | MkClassTable }}
### ⋔ Inheritance diagram
{{ cls | MkClassDiagram(mode="baseclasses") }}
{% endif %}

### 🛈 DocStrings

{{ cls | MkDocStrings }}
