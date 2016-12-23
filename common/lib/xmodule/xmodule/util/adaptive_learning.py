# -*- coding: utf-8 -*-
"""
Utilities for adaptive learning features.
"""

import json
import logging
import requests

from lazy import lazy

log = logging.getLogger(__name__)


class AdaptiveLearningConfiguration(object):
    """
    Stores configuration that is necessary for interacting with external services
    that provide adaptive learning features.
    """

    def __init__(self, **kwargs):
        """
        Creates an attribute for each key in `kwargs` and sets it to the corresponding value.
        """
        self._configuration = kwargs
        for attr, value in kwargs.items():
            setattr(self, attr, value)

    def __str__(self):
        """
        Returns string listing all custom attributes set on `self`.
        """
        return str(self._configuration)


class AdaptiveLearningAPIMixin(object):
    """
    Provides methods for interacting with external service that provides adaptive learning features.
    """

    @lazy
    def adaptive_learning_configuration(self):
        """
        Return configuration for accessing external service that provides adaptive learning features.

        This configuration is a course-wide setting, so in order to access it,
        we need to (lazily) load the parent course from the DB.
        """
        course = self.parent_course
        return AdaptiveLearningConfiguration(
            **course.adaptive_learning_configuration
        )

    @lazy
    def adaptive_learning_url(self):
        """
        Return base URL for external service that provides adaptive learning features.

        The base URL is a combination of the URL (url) and API version (api_version)
        specified in the adaptive learning configuration for the parent course.
        """
        url = self.adaptive_learning_configuration.url
        api_version = self.adaptive_learning_configuration.api_version
        return '{url}/{api_version}'.format(url=url, api_version=api_version)

    @lazy
    def instance_url(self):
        """
        Return URL for requesting instance-specific data from external service
        that provides adaptive learning features.
        """
        instance_id = self.adaptive_learning_configuration.instance_id
        return '{base_url}/instances/{instance_id}'.format(
            base_url=self.adaptive_learning_url, instance_id=instance_id
        )

    @lazy
    def students_url(self):
        """
        Return URL for requests dealing with students.
        """
        return '{base_url}/students'.format(base_url=self.instance_url)

    @lazy
    def events_url(self):
        """
        Return URL for requests dealing with events.
        """
        return '{base_url}/events'.format(base_url=self.instance_url)

    @lazy
    def knowledge_node_students_url(self):
        """
        Return URL for accessing 'knowledge node student' objects.
        """
        return '{base_url}/knowledge_node_students'.format(base_url=self.instance_url)

    @lazy
    def pending_reviews_url(self):
        """
        Return URL for accessing pending reviews.
        """
        return '{base_url}/review_utils/fetch_reviews'.format(base_url=self.instance_url)

    @lazy
    def request_headers(self):
        """
        Return custom headers for requests to external service that provides adaptive learning features.
        """
        access_token = self.adaptive_learning_configuration.access_token
        return {
            'Authorization': 'Token token={access_token}'.format(access_token=access_token)
        }

    def get_knowledge_node_student_id(self, block_id, user_id):
        """
        Return ID of 'knowledge node student' object linking student identified by `user_id`
        to unit identified by `block_id`.
        """
        knowledge_node_student = self.get_or_create_knowledge_node_student(block_id, user_id)
        return knowledge_node_student.get('id')

    def get_or_create_knowledge_node_student(self, block_id, user_id):
        """
        Return 'knowledge node student' object for user identified by `user_id`
        and unit identified by `block_id`.
        """
        # Create student
        self.get_or_create_student(user_id)
        # Link student to unit
        knowledge_node_student = self.get_knowledge_node_student(block_id, user_id)
        if knowledge_node_student is None:
            knowledge_node_student = self.create_knowledge_node_student(block_id, user_id)
        return knowledge_node_student

    def get_or_create_student(self, user_id):
        """
        Create a new student on external service if it doesn't exist,
        and return it.
        """
        student = self.get_student(user_id)
        if student is None:
            student = self.create_student(user_id)
        return student

    def get_student(self, user_id):
        """
        Return external information about student identified by `user_id`,
        or None if external service does not know about student.
        """
        students = self.get_students()
        try:
            student = next(s for s in students if s.get('uid') == user_id)
        except StopIteration:
            student = None
        return student

    def get_students(self):
        """
        Return list of all students that external service knows about.
        """
        url = self.students_url
        response = requests.get(url, headers=self.request_headers)
        students = json.loads(response.content)
        return students

    def create_student(self, user_id):
        """
        Create student identified by `user_id` on external service,
        and return it.
        """
        url = self.students_url
        payload = {'uid': user_id}
        response = requests.post(url, headers=self.request_headers, data=payload)
        student = json.loads(response.content)
        return student

    def get_knowledge_node_student(self, block_id, user_id):
        """
        Return 'knowledge node student' object for user identified by `user_id`
        and unit identified by `block_id`, or None if it does not exist.
        """
        # Get 'knowledge node student' objects
        links = self.get_knowledge_node_students()
        # Filter them by `block_id` and `user_id`
        try:
            link = next(
                l for l in links if l.get('knowledge_node_uid') == block_id and l.get('student_uid') == user_id
            )
        except StopIteration:
            link = None
        return link

    def get_knowledge_node_students(self):
        """
        Return list of all 'knowledge node student' objects for this course.
        """
        url = self.knowledge_node_students_url
        response = requests.get(url, headers=self.request_headers)
        links = json.loads(response.content)
        return links

    def create_knowledge_node_student(self, block_id, user_id):
        """
        Create 'knowledge node student' object that links student identified by `user_id`
        to unit identified by `block_id`, and return it.
        """
        url = self.knowledge_node_students_url
        payload = {'knowledge_node_uid': block_id, 'student_uid': user_id}
        response = requests.post(url, headers=self.request_headers, data=payload)
        knowledge_node_student = json.loads(response.content)
        return knowledge_node_student

    def create_read_event(self, block_id, user_id):
        """
        Create read event for unit identified by `block_id` and student identified by `user_id`.
        """
        return self.create_event(block_id, user_id, 'EventRead')

    def create_event(self, block_id, user_id, event_type):
        """
        Create event of type `event_type` for unit identified by `block_id` and student identified by `user_id`.
        """
        url = self.events_url
        knowledge_node_student_id = self.get_knowledge_node_student_id(block_id, user_id)
        payload = {
            'knowledge_node_student_id': knowledge_node_student_id,
            'event_type': event_type,
        }
        # Send request
        response = requests.post(url, headers=self.request_headers, data=payload)
        event = json.loads(response.content)
        return event

    def get_pending_reviews(self, user_id):
        """
        Return pending reviews for user identified by `user_id`.
        """
        url = self.pending_reviews_url
        payload = {'student_uid': user_id}
        response = requests.get(url, headers=self.request_headers, data=payload)
        pending_reviews_user = json.loads(response.content)
        return pending_reviews_user
