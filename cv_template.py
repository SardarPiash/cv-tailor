from documents import cv_blocks, render_docx, render_pdf


def docx(profile, cv):
    return render_docx(cv_blocks(profile, cv))


def pdf(profile, cv):
    return render_pdf(cv_blocks(profile, cv))
