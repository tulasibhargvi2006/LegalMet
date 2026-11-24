class RuleEngine:
    def validate(self, extracted_fields, rules):
        violations = []
        for rule in rules:
            field = rule['field']
            required = rule.get('required', False)
            severity = rule.get('severity', 'Medium')
            label = rule.get('label', field)

            value = extracted_fields.get(field, '')
            if required and not value:
                violations.append({
                    'field': field,
                    'label': label,
                    'severity': severity,
                    'message': f'{label} is missing.'
                })
        status = 'COMPLIANT' if not violations else 'NON-COMPLIANT'
        return {
            'status': status,
            'violations': violations,
            'extracted': extracted_fields,
            'summary': {
                'total_checks': len(rules),
                'passed': len(rules) - len(violations),
                'failed': len(violations)
            }
        }
