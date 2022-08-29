# ***[import_string]***
# ***[var_define]***
self.A = 'device'
self.D = 'device 1'
self.F = 'color'
self.V = {'red':[255,0,0], 'green':[0,255,0], 'blue':[0,0,255]}
# ***[init_content]***
voicetalk.update_table(type(self).__name__ ,self.A, self.D, self.F, self.V)
# ***[runs_content]***
Token = voicetalk.get_info(type(self).__name__)
if( (Token['A'] == self.A or Token['D'] ==self.D) and Token['F'] == self.F):
    if(Token['V'] in self.V):
        value = self.V[Token['V']]
    else:
        value = voicetalk.get_data(type(self).__name__)
    return value
else:
    return NoData