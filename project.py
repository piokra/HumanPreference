from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, jsonify
from flask_login import login_required, current_user

from . import db
from .models import Project

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

    return render_template('view_project_data.html', project_name=project_name)


@project.route('/old/project/compare/<project_name>')
@login_required
def project_compare_old(project_name):
    if not _is_authorized_to_use_project(project_name):
        flash("You are not authorized to access this project")
        return redirect(url_for('.project_view'))

    from .data_pika import DataQueue
    left, right = None, None
    try:
        channel = DataQueue(project_name)
        left, right = channel.pop_data(limit=1)[0].decode('ascii').split('||')
    except BaseException as e:  # todo more specific expection
        print(e, type(e))
        left, right = None, None
    return render_template('view_project_data.old.html', left=left, right=right, project_name=project_name)


@project.route('/project/api/compare/enqueue/<project_name>', methods=['POST'])
@login_required
def project_compare_enqueue(project_name):
    if not _is_authorized_to_use_project(project_name):
        return jsonify({'success': False, 'reason': 'Unauthorized'}), 401

    json = request.get_json()
    left, right, which = json["left"], json["right"], json["which"]

    from .data_pika import DataQueue

    dq = DataQueue(project_name)
    dq.push_data("{}||{}".format(left, right), which)

    return jsonify({'success': True})


@project.route('/project/api/compare/dequeue/<project_name>')
@login_required
def project_compare_dequeue(project_name):
    if not _is_authorized_to_use_project(project_name):
        return jsonify({'success': False, 'reason': 'Unauthorized'}), 401

    from .data_pika import DataQueue
    lefts, rights = [], []
    try:
        channel = DataQueue(project_name)
        data = channel.pop_data()
        for datum in data:
            left, right = datum.decode('ascii').split('||')
            lefts.append(left)
            rights.append(right)
    except BaseException as e:  # todo more specific expection
        print(e, type(e))

    return jsonify({'success': True, 'lefts': lefts, 'rights': rights})
