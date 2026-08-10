from typing import List

def generate_csv_response(
    targets: List,
    list_name: str,
    export_type: str = "all"
):
    """Generate CSV StreamingResponse from targets."""
    from fastapi.responses import StreamingResponse
    from datetime import datetime
    import re
    import io
    import csv

    output = io.StringIO()
    output.write('\ufeff')  # BOM for Excel

    fieldnames = ['email', 'first_name', 'last_name', 'position', 'department']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for target in targets:
        writer.writerow({
            'email': target.email or '',
            'first_name': target.first_name or '',
            'last_name': target.last_name or '',
            'position': target.position or '',
            'department': target.department or ''
        })

    output.seek(0)
    csv_content = output.getvalue()

    # Sanitize filename
    safe_name = re.sub(r'[^\w\s-]', '', list_name)
    safe_name = re.sub(r'[-\s]+', '_', safe_name)
    timestamp = datetime.now().strftime('%Y-%m-%d')
    filename = f"{safe_name}_{export_type}_targets_{timestamp}.csv"

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/csv; charset=utf-8",
            "X-Total-Records": str(len(targets))
        }
    )
