def next_id():
    id = getattr(next_id, 'id', 1) + 1
    setattr(next_id, 'id', id)
    return id


class Blog:
    def __init__(self, title, content, id=None):
        self.id = id or next_id()
        self.title = title
        self.content = content


blog_db = {}


def save(blog):
    blog_db[blog.id] = blog


def all():
    return blog_db.values()


def get(blog_id):
    return blog_db.get(blog_id, None)


def delete(blog_id):
    blog_db.pop(blog_id, None)
