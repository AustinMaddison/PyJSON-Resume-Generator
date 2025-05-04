
# Run with defaults
```bash
python resume-generator.py
```

# Exclude certain sections
```bash
python resume-generator.py --exclude=certifications,education
```

# Include only specific sections
```bash
python resume-generator.py --sections=header,summary,experience,projects
```

# Limit number of projects
```bash
python resume-generator.py --max-projects=3
```

# Change JSON file paths
```python resume-generator.py --base-json=./custom/base.json --projects-json=./custom/projects.jsonbash

```

# Change output directory and port
```bash
python resume-generator.py --output-dir=./output --port=8080
```