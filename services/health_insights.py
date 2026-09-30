from models import MedicationLog, SymptomLog, HealthScore, ReportLog
from datetime import datetime, timedelta
import json


def generate_health_insights(user):
    insights = []
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    previous_week = now - timedelta(days=14)

    # Medication insights
    current_med_logs = MedicationLog.query.filter(
        MedicationLog.user_id == user.id,
        MedicationLog.logged_at >= week_ago
    ).all()

    previous_med_logs = MedicationLog.query.filter(
        MedicationLog.user_id == user.id,
        MedicationLog.logged_at >= previous_week,
        MedicationLog.logged_at < week_ago
    ).all()

    current_taken = sum(
        1 for log in current_med_logs if log.status == 'taken'
    )
    current_missed = sum(
        1 for log in current_med_logs if log.status == 'missed'
    )

    current_total = current_taken + current_missed

    if current_total > 0:
        adherence = current_taken / current_total

        if previous_med_logs:
            previous_taken = sum(
                1 for log in previous_med_logs if log.status == 'taken'
            )
            previous_missed = sum(
                1 for log in previous_med_logs if log.status == 'missed'
            )
            previous_total = previous_taken + previous_missed

            if previous_total > 0:
                previous_adherence = previous_taken / previous_total

                if adherence > previous_adherence + 0.05:
                    insights.append({
                        'type': 'success',
                        'icon': 'capsule-pill',
                        'title': 'Medication adherence improved',
                        'message': (
                            f'You logged {current_taken} of '
                            f'{current_total} doses this week, '
                            f'up from {previous_adherence:.0%} last week.'
                        )
                    })
                elif adherence < previous_adherence - 0.05:
                    insights.append({
                        'type': 'warning',
                        'icon': 'capsule-pill',
                        'title': 'Medication adherence decreased',
                        'message': (
                            f'You logged {current_taken} of '
                            f'{current_total} doses this week. '
                            f'Your adherence was {previous_adherence:.0%} last week.'
                        )
                    })

        if adherence >= 0.9:
            insights.append({
                'type': 'success',
                'icon': 'check-circle',
                'title': 'Strong medication pattern',
                'message': (
                    f'You took {current_taken} of {current_total} '
                    f'logged doses in the last 7 days.'
                )
            })
        elif adherence < 0.7:
            insights.append({
                'type': 'warning',
                'icon': 'exclamation-triangle',
                'title': 'Medication pattern needs attention',
                'message': (
                    f'{current_missed} of your {current_total} '
                    f'logged doses were marked missed this week.'
                )
            })

    # Symptom insights
    recent_symptoms = SymptomLog.query.filter(
        SymptomLog.user_id == user.id,
        SymptomLog.logged_at >= week_ago
    ).all()

    symptom_count = len(recent_symptoms)
    high_severity = sum(
        1 for symptom in recent_symptoms
        if symptom.severity and symptom.severity >= 7
    )

    if high_severity > 0:
        insights.append({
            'type': 'danger',
            'icon': 'activity',
            'title': 'High-severity symptoms recorded',
            'message': (
                f'You recorded {high_severity} high-severity '
                f'symptom log(s) in the last 7 days. '
                f'Consider discussing persistent or severe symptoms '
                f'with a qualified healthcare professional.'
            )
        })
    elif symptom_count >= 3:
        insights.append({
            'type': 'info',
            'icon': 'activity',
            'title': 'Increased symptom activity',
            'message': (
                f'You recorded {symptom_count} symptom entries '
                f'in the last 7 days. Tracking whether these symptoms '
                f'recur can help provide useful information to your doctor.'
            )
        })
    elif symptom_count > 0:
        insights.append({
            'type': 'info',
            'icon': 'activity',
            'title': 'Recent symptom activity',
            'message': (
                f'You recorded {symptom_count} symptom '
                f'entry in the last 7 days.'
            )
        })

    # Health score trend
    scores = HealthScore.query.filter(
        HealthScore.user_id == user.id,
        HealthScore.computed_at >= previous_week
    ).order_by(HealthScore.computed_at.asc()).all()

    if len(scores) >= 2:
        first_score = scores[0].score
        latest_score = scores[-1].score
        difference = latest_score - first_score

        if difference >= 5:
            insights.append({
                'type': 'success',
                'icon': 'graph-up-arrow',
                'title': 'Health score trend improved',
                'message': (
                    f'Your activity-based health score increased '
                    f'from {first_score:.0f} to {latest_score:.0f} '
                    f'during the recorded period.'
                )
            })
        elif difference <= -5:
            insights.append({
                'type': 'warning',
                'icon': 'graph-down-arrow',
                'title': 'Health score trend changed',
                'message': (
                    f'Your activity-based health score changed '
                    f'from {first_score:.0f} to {latest_score:.0f}. '
                    f'Review your recent health activity for context.'
                )
            })
        else:
            insights.append({
                'type': 'info',
                'icon': 'activity',
                'title': 'Health score remains stable',
                'message': (
                    f'Your activity-based health score has remained '
                    f'relatively stable around {latest_score:.0f}.'
                )
            })

    # Report insights
    reports = ReportLog.query.filter(
        ReportLog.user_id == user.id
    ).order_by(
        ReportLog.logged_at.desc()
    ).limit(10).all()

    if reports:
        latest_report = reports[0]

        try:
            latest_metrics = json.loads(latest_report.key_metrics or '[]')
        except (json.JSONDecodeError, TypeError):
            latest_metrics = []

        latest_abnormal = [
            metric for metric in latest_metrics
            if metric.get('status') in ['High', 'Low']
        ]

        if latest_abnormal:
            insights.append({
                'type': 'warning',
                'icon': 'file-earmark-medical',
                'title': 'Recent report findings',
                'message': (
                    f'Your latest {latest_report.report_type.lower()} '
                    f'contains {len(latest_abnormal)} parameter(s) '
                    f'outside the reference ranges stated in the report.'
                )
            })

        if len(reports) >= 2:
            previous_report = reports[1]

            try:
                previous_metrics = json.loads(
                    previous_report.key_metrics or '[]'
                )
            except (json.JSONDecodeError, TypeError):
                previous_metrics = []

            previous_values = {
                metric.get('parameter'): metric.get('value')
                for metric in previous_metrics
                if metric.get('parameter') and isinstance(
                    metric.get('value'), (int, float)
                )
            }

            changed_parameters = []

            for metric in latest_metrics:
                parameter = metric.get('parameter')
                current_value = metric.get('value')

                if (
                    parameter in previous_values
                    and isinstance(current_value, (int, float))
                ):
                    previous_value = previous_values[parameter]

                    if current_value != previous_value:
                        changed_parameters.append(
                            (parameter, previous_value, current_value)
                        )

            if changed_parameters:
                parameter, previous_value, current_value = changed_parameters[0]

                direction = (
                    'increased'
                    if current_value > previous_value
                    else 'decreased'
                )

                insights.append({
                    'type': 'info',
                    'icon': 'graph-up-arrow' if direction == 'increased'
                    else 'graph-down-arrow',
                    'title': 'Report value changed',
                    'message': (
                        f'{parameter} {direction} from '
                        f'{previous_value:g} to {current_value:g} '
                        f'between your two most recent reports.'
                    )
                })

    return insights[:5]