from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user

from . import db
from .models import Project

import data_pika

project = Blueprint('project', __name__)


@project.route('/project/create')
@login_required
def project_create():
    return render_template('create_project.html')


@project.route('/project/create', methods=['POST'])
@login_required
def project_create_post():
    project_name = request.form.get('project_name')
    description = request.form.get('description')

    project_obj = Project.query.filter_by(name=project_name).first()
    if project_obj:
        flash("Project name taken")
        return redirect(url_for('.project_create'))

    project_obj = Project(name=project_name, description=description)
    project_obj.owners.append(current_user)

    db.session.add(project_obj)
    db.session.commit()

    return redirect(url_for('.project_view'))


@project.route('/project/view')
@login_required
def project_view():
    projects = Project.query.all()
    accessible_projects = []
    for _project in projects:
        if current_user in _project.owners or current_user in _project.authorized_users:
            accessible_projects.append(_project)
    return render_template('view_projects.html', projects=accessible_projects)


def _is_authorized_to_use_project(project_name):
    selected_project: Project = Project.query.filter_by(name=project_name).first()
    if selected_project is None or \
            (current_user not in selected_project.owners and current_user not in selected_project.authorized_users):
        return False
    return True


@project.route('/project/compare/<project_name>')
@login_required
def project_compare(project_name):
    if not _is_authorized_to_use_project(project_name):
        flash("You are not authorized to access this project")
        return redirect(url_for('.project_view'))

    from .data_pika import DataQueue
    channel = DataQueue(project_name)
    channel.await_data()

    return render_template('view_project_data.html', left="Boobs", right='Ass')


@project.route('/project/compare/<project_name>', methods=['POST'])
@login_required
def project_compare_post(project_name):
    if not _is_authorized_to_use_project(project_name):
        return abort(401)

    left, right, which = request.form["left"], request.form["right"], request.form["which"]
