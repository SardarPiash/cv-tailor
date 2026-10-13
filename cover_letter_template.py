from documents import cover_blocks, render_docx, render_pdf


def docx(profile, letter, company, application_date=None):
    return render_docx(cover_blocks(profile, letter, company, application_date))


def pdf(profile, letter, company, application_date=None):
    return render_pdf(cover_blocks(profile, letter, company, application_date))
