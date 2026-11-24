# from config import RULES, MANDATORY_FIELDS

# class RuleEngine:
#     def __init__(self):
#         self.rules = RULES

#     def validate(self, extracted_fields):
#         """Check extracted fields against rules and return violations."""
#         violations = []
#         compliance_status = 'COMPLIANT'

#         for rule in self.rules:
#             field = rule['field']
#             required = rule['required']
#             severity = rule['severity']

#             value = extracted_fields.get(field, '')
#             if required and not value:
#                 violations.append({
#                     'field': field,
#                     'label': MANDATORY_FIELDS.get(field, field),
#                     'severity': severity,
#                     'message': f'{MANDATORY_FIELDS.get(field, field)} is missing.'
#                 })
#             elif not required and value:
#                 # optional field present – no issue
#                 pass
#             # Additional checks could be added: e.g., format validation for dates, MRP numeric, etc.

#         if violations:
#             compliance_status = 'NON-COMPLIANT'

#         return {
#             'status': compliance_status,
#             'violations': violations,
#             'extracted': extracted_fields,
#             'summary': {
#                 'total_checks': len(self.rules),
#                 'passed': len(self.rules) - len(violations),
#                 'failed': len(violations)
#             }
#         }

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