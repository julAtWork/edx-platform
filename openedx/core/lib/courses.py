"""
Common utility functions related to courses.
"""
from django.conf import settings

from xmodule.modulestore.django import modulestore
from xmodule.contentstore.content import StaticContent
from xmodule.modulestore import ModuleStoreEnum as MSE


def course_image_url(course):
    """Try to look up the image url for the course.  If it's not found,
    log an error and return the dead link"""
    if course.static_asset_path or \
        modulestore().get_modulestore_type(course.id) == MSE.Type.xml:
        # If we are a static course with the course_image attribute
        # set different than the default, return that path so that
        # courses can use custom course image paths, otherwise just
        # return the default static path.
        url = '/static/' + (course.static_asset_path or \
                getattr(course, 'data_dir', ''))
        if hasattr(course, 'course_image') and \
            course.course_image != course.fields['course_image'].default:
            url += '/' + course.course_image
        else:
            url += '/images/course_image.jpg'
        return url
        # if course_image is empty, use the default image url from settings


    if course.course_image:
        loc = StaticContent.compute_location(course.id, course.course_image)
        url = StaticContent.serialize_asset_key_with_slash(loc)
        return url
    url = ""

    try:
        url = settings.STATIC_URL + settings.DEFAULT_COURSE_ABOUT_IMAGE_URL
    except AttributeError as excep:
        # AttributeError: 'Settings' object has no attribute 'DEFAULT_COURSE_ABOUT_IMAGE_URL'
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("You should check your settings (%r)", excep)

    return url

