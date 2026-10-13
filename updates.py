import copy
from schemas import Profile, Suggestion


def apply_suggestion(profile, suggestion):
    suggestion = Suggestion.model_validate(suggestion).model_dump()
    p = copy.deepcopy(profile)
    if suggestion['kind'] == 'skill':
        if not suggestion['value'] or not suggestion['category']:
            raise ValueError('Skill and category are required.')
        group = next((g for g in p['skills'] if g['category'].casefold() == suggestion['category'].casefold()), None)
        if group is None:
            group = {'category': suggestion['category'], 'items': []}
            p['skills'].append(group)
        if suggestion['value'].casefold() not in [x.casefold() for x in group['items']]:
            group['items'].append(suggestion['value'])
    elif suggestion['kind'] == 'experience_bullet':
        index = suggestion['target_index']
        if index is None or index < 0 or index >= len(p['experience']) or not suggestion['value']:
            raise ValueError('Choose a valid experience index and enter an achievement bullet.')
        if suggestion['value'] not in p['experience'][index]['bullets']:
            p['experience'][index]['bullets'].append(suggestion['value'])
    elif suggestion['kind'] == 'project':
        if not suggestion['project'] or not suggestion['project']['name']:
            raise ValueError('A project with a real name is required.')
        p['projects'].append(suggestion['project'])
    return Profile.model_validate(p).model_dump()
