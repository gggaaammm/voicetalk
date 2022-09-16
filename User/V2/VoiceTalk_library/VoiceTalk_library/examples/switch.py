# ***[import_string]***
# ***[var_define]***
# D = Device, A = Action, V = Value
# self.D = 'device'
# self.A = {'open':1, 'close':0}
# self.V = None
self.D = 'device'
self.A = {'open':1, 'close':0}
self.V = None
# ***[init_content]***
voicetalk.update_table(type(self).__name__ ,self.D, self.A, self.V, Language)
# ***[runs_content]***
Token = voicetalk.get_info(type(self).__name__)
if( Token['D'] == self.D and Token['A'] ==self.A):
    value = voicetalk.get_data(type(self).__name__)
    return value
else:
    return NoData