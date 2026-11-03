---
name: feature-code-review
description: Permite sugerir mejoras y detectar malas practicas de programación basados en principios SOLID.
---

# Skill: Feature Code Review

## 1) Metadata
- **Skill ID:** feature-code-review
- **Version:** 0.1.0
- **Purpose:** Sugerir mejoras y detectar malas practicas de programación basados en principios SOLID.

## 2) Inputs
- **Ruta:** Ruta del archivo o directorio que se desea revisar.

## 3) Output
- **Output file:** Devuelve un archivo .mermaid con el diagrama de secuencia generado.
- **Report file:** reporte en formato .md que contiene los datos relevantes del diagrama de secuencia generado.

## 4) Constraints
- No inventes interacciones que no estén definidas en el flujo.
- Mantén la consistencia con los nombres de los componentes y endpoints utilizados en el flujo.
- No incluyas datos sensibles ni secretos en el diagrama.
- Asegúrate de que el diagrama sea comprensible y refleje fielmente el flujo de interacción definido.
- No incluyas clases constantes en el diagrama.
- Asegúrate de que todas las interacciones estén correctamente ordenadas temporalmente.
- Verifica que el diagrama sea compatible con el formato Mermaid y pueda ser renderizado correctamente.
## 5) Validation Rules
La salida es válida si:
- El diagrama refleja fielmente el flujo de interacción definido.
- Todas las interacciones están correctamente ordenadas temporalmente.
- No se incluyen datos sensibles ni secretos.
- El diagrama es compatible con el formato Mermaid y puede ser renderizado correctamente.
- No se incluyen clases constantes en el diagrama.
- Todas las interacciones están correctamente etiquetadas y documentadas.
- El diagrama es comprensible y refleja fielmente el flujo de interacción definido.
- No se incluyen elementos innecesarios o redundantes en el diagrama.

## 6) Evidence
Adjunta o referencia estos elementos en el PR o entrega:
- `SKILL.md` versionado.
- Archivo de salida generados en la carpeta docs, incluyendo el archivo .mermaid y el reporte en formato .md.
- Tag de versión para el Skill, como `skill-feature-generate-sequence-diagram-v0.1.0`.