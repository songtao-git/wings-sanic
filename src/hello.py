from schema import serializers


class Person:
    def __init__(self, name, age=None, id=None):
        self.id = id
        self.name = name
        self.age = age


class PersonSerializer(serializers.Serializer):
    name = serializers.StringField('姓名')
    age = serializers.IntField('年龄')

    class Meta:
        serialize_when_none = True

if __name__ == '__main__':
    p = Person('songtao')
    person_s = PersonSerializer('人', fields={'id': serializers.IDField('身份证', required=True)})
    print(person_s.validate(p, context={'serialize_when_none': True}))
