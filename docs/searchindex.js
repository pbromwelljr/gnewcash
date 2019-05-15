Search.setIndex({docnames:["account","code_documentation","commodity","file_formats","gnucash_file","guid_object","index","overview","slot","transaction","usage","utils","versions"],envversion:{"sphinx.domains.c":1,"sphinx.domains.changeset":1,"sphinx.domains.cpp":1,"sphinx.domains.javascript":1,"sphinx.domains.math":2,"sphinx.domains.python":1,"sphinx.domains.rst":1,"sphinx.domains.std":1,"sphinx.ext.intersphinx":1,"sphinx.ext.viewcode":1,sphinx:55},filenames:["account.rst","code_documentation.rst","commodity.rst","file_formats.rst","gnucash_file.rst","guid_object.rst","index.rst","overview.rst","slot.rst","transaction.rst","usage.rst","utils.rst","versions.rst"],objects:{"":{account:[11,0,0,"-"],commodity:[2,0,0,"-"],file_formats:[3,0,0,"-"],gnucash_file:[4,0,0,"-"],guid_object:[5,0,0,"-"],slot:[8,0,0,"-"],transaction:[9,0,0,"-"],utils:[11,0,0,"-"]},"account.Account":{as_dict:[0,2,1,""],as_xml:[0,3,1,""],color:[0,3,1,""],dict_entry_name:[0,3,1,""],from_sqlite:[0,4,1,""],from_xml:[0,4,1,""],get_account_guids:[0,2,1,""],get_parent_commodity:[0,2,1,""],get_subaccount_by_id:[0,2,1,""],hidden:[0,3,1,""],notes:[0,3,1,""],parent:[0,3,1,""],placeholder:[0,3,1,""],to_sqlite:[0,2,1,""]},"account.InterestAccount":{__init__:[0,2,1,""],get_all_payments:[0,2,1,""],get_info_at_date:[0,2,1,""],interest_percentage:[0,3,1,""],payment_amount:[0,3,1,""],starting_balance:[0,3,1,""],starting_date:[0,3,1,""]},"account.InterestAccountBase":{get_all_payments:[0,2,1,""],get_info_at_date:[0,2,1,""],interest_percentage:[0,3,1,""],payment_amount:[0,3,1,""],starting_balance:[0,3,1,""],starting_date:[0,3,1,""]},"account.InterestAccountWithSubaccounts":{__init__:[0,2,1,""],get_all_payments:[0,2,1,""],get_info_at_date:[0,2,1,""],interest_percentage:[0,3,1,""],payment_amount:[0,3,1,""],starting_balance:[0,3,1,""],starting_date:[0,3,1,""]},"account.LoanExtraPayment":{payment_amount:[0,3,1,""],payment_date:[0,3,1,""]},"account.LoanStatus":{amount_to_capital:[0,3,1,""],interest:[0,3,1,""],iterator_balance:[0,3,1,""],iterator_date:[0,3,1,""]},"commodity.Commodity":{as_short_xml:[2,2,1,""],as_xml:[2,3,1,""],from_sqlite:[2,4,1,""],from_xml:[2,4,1,""],to_sqlite:[2,2,1,""]},"file_formats.DBAction":{INSERT:[3,3,1,""],UPDATE:[3,3,1,""]},"file_formats.FileFormat":{GZIP_XML:[3,3,1,""],SQLITE:[3,3,1,""],UNKNOWN:[3,3,1,""],XML:[3,3,1,""]},"file_formats.GnuCashSQLiteObject":{from_sqlite:[3,4,1,""],get_db_action:[3,4,1,""],get_sqlite_table_data:[3,4,1,""],to_sqlite:[3,2,1,""]},"file_formats.GnuCashXMLObject":{as_xml:[3,3,1,""],from_xml:[3,4,1,""]},"gnucash_file.Book":{as_xml:[4,3,1,""],from_sqlite:[4,4,1,""],from_xml:[4,4,1,""],get_account:[4,2,1,""],get_account_balance:[4,2,1,""],to_sqlite:[4,2,1,""]},"gnucash_file.Budget":{as_xml:[4,3,1,""],from_sqlite:[4,4,1,""],from_xml:[4,4,1,""],to_sqlite:[4,2,1,""]},"gnucash_file.GnuCashFile":{build_file:[4,2,1,""],create_sqlite_schema:[4,4,1,""],detect_file_format:[4,4,1,""],read_file:[4,4,1,""]},"guid_object.GuidObject":{get_guid:[5,4,1,""]},"slot.Slot":{as_xml:[8,3,1,""],from_sqlite:[8,4,1,""],from_xml:[8,4,1,""],to_sqlite:[8,2,1,""]},"slot.SlottableObject":{get_slot_value:[8,2,1,""],set_slot_value:[8,2,1,""],set_slot_value_bool:[8,2,1,""]},"transaction.ScheduledTransaction":{as_xml:[9,3,1,""],from_sqlite:[9,4,1,""],from_xml:[9,4,1,""],read_xml_child_boolean:[9,4,1,""],read_xml_child_date:[9,4,1,""],read_xml_child_int:[9,4,1,""],read_xml_child_text:[9,4,1,""],to_sqlite:[9,2,1,""]},"transaction.SimpleTransaction":{amount:[9,3,1,""],from_account:[9,3,1,""],from_xml:[9,4,1,""],to_account:[9,3,1,""]},"transaction.Split":{as_xml:[9,3,1,""],from_sqlite:[9,4,1,""],from_xml:[9,4,1,""],to_sqlite:[9,2,1,""]},"transaction.Transaction":{as_xml:[9,3,1,""],associated_uri:[9,3,1,""],cleared:[9,3,1,""],from_sqlite:[9,4,1,""],from_xml:[9,4,1,""],mark_transaction_cleared:[9,2,1,""],notes:[9,3,1,""],reversed_by:[9,3,1,""],to_sqlite:[9,2,1,""],void_reason:[9,3,1,""],void_time:[9,3,1,""],voided:[9,3,1,""]},"transaction.TransactionManager":{"delete":[9,2,1,""],add:[9,2,1,""],get_account_ending_balance:[9,2,1,""],get_account_starting_balance:[9,2,1,""],get_balance_at_date:[9,2,1,""],get_transactions:[9,2,1,""],minimum_balance_past_date:[9,2,1,""]},account:{Account:[0,1,1,""],AccountType:[0,1,1,""],AssetAccount:[0,1,1,""],BankAccount:[0,1,1,""],CreditAccount:[0,1,1,""],EquityAccount:[0,1,1,""],ExpenseAccount:[0,1,1,""],IncomeAccount:[0,1,1,""],InterestAccount:[0,1,1,""],InterestAccountBase:[0,1,1,""],InterestAccountWithSubaccounts:[0,1,1,""],LiabilityAccount:[0,1,1,""],LoanExtraPayment:[0,1,1,""],LoanStatus:[0,1,1,""]},commodity:{Commodity:[2,1,1,""]},file_formats:{DBAction:[3,1,1,""],FileFormat:[3,1,1,""],GnuCashSQLiteObject:[3,1,1,""],GnuCashXMLObject:[3,1,1,""]},gnucash_file:{Book:[4,1,1,""],Budget:[4,1,1,""],GnuCashFile:[4,1,1,""]},guid_object:{GuidObject:[5,1,1,""]},slot:{Slot:[8,1,1,""],SlottableObject:[8,1,1,""]},transaction:{ScheduledTransaction:[9,1,1,""],SimpleTransaction:[9,1,1,""],Split:[9,1,1,""],Transaction:[9,1,1,""],TransactionManager:[9,1,1,""]},utils:{delete_log_files:[11,5,1,""],safe_iso_date_formatting:[11,5,1,""],safe_iso_date_parsing:[11,5,1,""]}},objnames:{"0":["py","module","Python module"],"1":["py","class","Python class"],"2":["py","method","Python method"],"3":["py","attribute","Python attribute"],"4":["py","classmethod","Python class method"],"5":["py","function","Python function"]},objtypes:{"0":"py:module","1":"py:class","2":"py:method","3":"py:attribute","4":"py:classmethod","5":"py:function"},terms:{"abstract":[0,2,3,4,8,9],"boolean":9,"case":8,"catch":11,"class":[0,2,3,4,5,8,9,10],"default":[4,9,10],"final":10,"function":[8,9,10],"import":10,"int":[4,9],"long":10,"new":[0,4,5,8,10],"return":[0,2,3,4,5,8,9,10,11],"short":2,"true":[0,4,8,9],"try":[4,10],"void":[9,12],Added:12,Adding:12,And:10,For:10,That:10,The:10,There:10,Use:4,Using:6,Will:10,__init__:0,abov:[7,10],accept:10,access:10,account:[1,2,4,6,9,12],account_class:10,account_class_object:10,account_data:10,account_data_fil:10,account_guid:0,account_hierarchi:0,account_id:0,account_lookup:10,account_nod:0,account_object:[0,9,10],account_par:10,account_type_map:10,account_type_str:10,accounttyp:[0,10],accumul:10,action:[3,7],actual:10,add:[7,9,10],added:10,addit:[0,10],additional_pay:[0,10],after:9,alia:0,all:[0,2,7,9,10,11],allow:[0,7],alpha:0,alreadi:[0,9],also:[7,10],altern:7,although:10,amount:[0,9,10],amount_to_capit:[0,10],ancestor:0,ancestri:0,ani:[3,8,10],api:0,appear:10,applic:[4,9],appropri:3,apr:10,aren:10,arg:3,argument:[4,10],as_dict:0,as_short_xml:2,as_xml:[0,2,3,4,8,9],asset:[0,4,10],assetaccount:[0,10],assets_account:10,assign:[0,9,10],associ:[9,10],associated_uri:[9,12],assum:[0,4,10],attempt:11,automat:10,avail:[0,10],back:[7,10],balanc:[0,4,9,10],bank:[0,10],bankaccount:[0,10],base:[0,3,4,9,10],befor:[4,7,10],beforehand:10,behind:10,being:[3,4,10],belong:8,best:10,better:10,bill:10,bills_account:10,bind:7,bit:10,book:[4,6],book_nod:4,bool:[0,4,8,9,10],both:10,bucket:10,budget:[4,12],budget_nod:4,bugfix:12,build_fil:[4,10],built:7,calcul:[0,10],call:[0,10],can:[3,10],capit:0,card:10,care:10,certain:[8,9,10],chain:0,chang:10,charact:0,check:[3,4,9,10],checking_account:10,checking_transact:10,child:[0,9],children:[0,10],chronolog:9,classmethod:[0,2,3,4,5,8,9],clear:[9,10],cmdty:10,code:[6,7,10],collect:10,color:[0,12],column:3,column_nam:3,come:10,comment:6,commod:[0,1,4,6],commodity_guid:2,commodity_id:2,commodity_nod:2,compat:[0,2,4,6,8,9],compress:[4,10],compris:10,concern:6,condit:3,configur:0,consid:9,consist:10,consolid:8,constructor:10,contain:[0,9,10,11],content:[4,6],convert:[0,3,8,10],corrupt:7,creat:[0,2,3,4,8,9],create_sqlite_schema:4,credit:[0,10],credit_card:10,credit_card_account:10,creditaccount:[0,10],ct_co:4,currenc:10,current:[0,2,4,8,9,10],current_asset:10,current_assets_account:10,current_level:4,current_path:10,cursor:[0,2,3,4,8,9],cut:10,data:[3,7,10],databas:[0,2,3,4,8,9],date:[0,9,10,11],date_ent:10,date_obj:11,date_post:[4,10],date_str:11,datetim:[0,9,10,11],dbaction:3,debit:10,decim:[0,4,9,10],def:10,defin:[0,10],delet:[9,11],delete_log_fil:11,depend:10,describ:10,descript:10,design:[7,10],detect:4,detect_file_format:4,determin:[3,9],develop:7,dict:[0,2,3,4,8,9,10],dict_entry_nam:0,dictionari:[0,3],differ:10,directori:11,disabl:10,disable_sort:10,disk:[4,10],document:10,doe:10,dollar:[9,10],done:10,down:10,each:[3,10],easier:[10,12],eastern:10,effici:10,either:10,element:[0,2,3,4,8,9],elementtre:[0,2,3,4,8,9],els:10,end:[9,10],entri:[0,10],enumer:[0,3],equiti:[0,10],equityaccount:[0,10],error:10,essenti:10,etre:[0,2,4,8,9],event:7,everyon:10,exampl:[4,10],exist:[0,3,10],expect:8,expens:[0,10],expenseaccount:[0,10],expenses_account:10,express:7,extra:0,fail:11,fals:[0,4,8,9,10],feel:10,field:[0,10],file:[1,6,7,10,11],file_format:[0,3,4],fileformat:[3,4],find:[0,3,7,9,10],first:[0,9,10],flag:[0,4],flat:0,follow:[7,10],format:[1,4,6,11],found:[0,4,9],free:10,from:[0,2,3,4,8,9,10],from_account:[9,10],from_sqlit:[0,2,3,4,8,9],from_xml:[0,2,3,4,8,9],full:4,fund:9,gdate:9,gener:[5,9,10],get:[0,9,10],get_account:[4,10],get_account_bal:4,get_account_ending_bal:[9,10],get_account_guid:0,get_account_starting_bal:[9,10],get_account_typ:10,get_all_pay:[0,10],get_balance_at_d:[9,10],get_db_act:3,get_guid:5,get_info_at_d:[0,10],get_parent_commod:0,get_quot:10,get_slot_valu:8,get_sqlite_table_data:3,get_subaccount_by_id:[0,12],get_transact:[9,10],given:[8,9,10],gnc:10,gnewcash:[0,4,5,9,11],gnucash:[0,1,2,3,6,7,8,9,10],gnucash_fil:4,gnucash_file_path:11,gnucashfil:[4,6],gnucashsqliteobject:[0,3],gnucashxmlobject:[0,3],goe:10,going:10,guid:[0,1,6,9,12],guid_object:[0,5],guidobject:[0,5],gzip:[4,10],gzip_xml:3,happi:10,has:9,have:[9,10],help:[10,11],helper:[3,8],here:10,hidden:[0,12],hierarchi:[0,10],highli:7,hold:7,how:10,identifi:3,implement:10,incom:[0,10],incomeaccount:[0,10],incorrectli:7,incur:10,index:0,indic:[0,4,9,10],info:0,inform:[10,11],initi:[0,4,12],inner:9,insensit:8,insert:3,insid:10,instal:6,integ:9,interact:7,interest:0,interest_percentag:[0,10],interest_start_d:[0,10],interestaccount:[0,10],interestaccountbas:0,interestaccountwithsubaccount:[0,10],isn:10,iso4217:10,issu:[7,10],iter:[9,10],iterator_bal:[0,10],iterator_d:[0,10],its:[0,9,12],itself:10,jan:12,json:10,json_fil:10,just:10,kei:[0,3,8],keyword:4,kwarg:[3,4],last:9,least:10,liabil:[0,6,10],liabilityaccount:[0,10],librari:7,licens:7,like:10,line:10,linux:7,list:[0,2,3,4,7,8,9,10],load:[0,4,9,10],load_account_and_subaccount:10,load_accounts_from_json:10,loader:10,loan:[0,10],loanextrapay:[0,10],loanstatu:[0,10],log:11,look:0,mac:7,magic:10,maintain:[9,10],make:12,manag:9,manipul:[9,12],mark:[0,9],mark_transaction_clear:[9,10],memo:10,memori:[4,10],method:[0,2,3,4,8,9,10,11,12],might:11,minimum:[0,9,10],minimum_balance_past_d:[9,10],mit:7,modifi:[7,10],monei:10,more:10,most:10,much:10,my_book:10,my_commod:10,my_fil:10,my_loan:10,my_new_transact:10,my_root_account:10,my_transaction_manag:10,name:[0,2,3,4,8,9,10],namedtupl:10,namespac:[0,2,3,4,8,9],need:[3,10],new_transact:9,node:[0,2,3,4,8,9],node_tag:2,none:[0,2,3,4,8,9,10,11],nonetyp:[0,4],note:[0,9,10,12],now:10,num:10,number:0,numer:0,object:[0,1,2,3,4,6,8,9,10,11],object_id:8,odul:11,off:[0,10],one:10,onli:[0,7,9,10,12],open:[0,2,3,4,8,9,10],oper:[3,7],option:[0,4,9,10],order:[9,10],osx:7,otherwis:[0,4,9],our:[7,10],out:4,over:10,overal:10,overview:6,overwrit:10,own:10,packag:7,paid:0,paramet:[0,2,3,4,8,9,10,11],parent:[0,9,10],pars:11,particular:10,pass:10,past:10,path:[4,10],path_to_self:0,paths_to_account:4,payment:[0,10],payment_amount:[0,10],payment_d:0,percentag:0,perform:7,person:10,phone:10,phone_account:10,phone_bil:10,pip:7,place:10,placehold:[0,12],plan:[0,10],pleas:[7,10],post:[9,10],practic:10,prefer:10,pretti:10,prettifi:[4,10],prettify_xml:[4,10],princip:10,probabl:10,produc:9,program:10,properti:[10,12],provid:[0,4,9,10],pull:2,purchas:10,pure:10,purpos:10,pytz:10,queri:3,question:6,quote_sourc:10,quote_tz:10,rais:[0,4],read:[3,4,7,9,10],read_fil:[4,10],read_xml_child_boolean:9,read_xml_child_d:9,read_xml_child_int:9,read_xml_child_text:9,real:10,reason:9,recommend:[7,10],reconciled_st:[9,10],reconcili:10,record:3,recurs:0,rel:4,releas:[7,12],reli:[7,10],remov:[9,10],rent:10,rent_account:10,repres:[0,2,4,8,9,10],requir:10,respons:10,result:10,retriev:[0,3,4,5,8,9,12],revers:9,reversed_bi:[9,12],review:10,root:[4,9,10],root_account:[4,9,10],row:3,row_identifi:3,rtype:4,run:[0,7],runtimeerror:4,safe_iso_date_format:11,safe_iso_date_pars:11,same:10,scene:10,schedul:[9,10],scheduled_transact:4,scheduledtransact:[4,9,12],schema:4,search:4,see:10,set:[0,8,10],set_slot_valu:8,set_slot_value_bool:8,sever:10,shortcut:[1,10],should:[0,4,7,10],show:0,side:8,simpletransact:[9,10,12],simpli:[7,10],simplifi:9,skip:[0,10],skip_additional_pay:0,skip_payment_d:[0,10],slash:0,slot:[0,1,4,6],slot_nod:8,slot_typ:8,slottableobject:[0,8],smaller:10,some:10,sort:[4,10],sort_transact:[4,10],sourc:[0,2,3,4,5,8,9,11],source_fil:4,space:[0,2,10],special:[1,10],specif:9,specifi:[0,4,9,10,11],split:[9,10,12],split_nod:9,sql:3,sqlite3:[0,2,3,4,8,9],sqlite:[0,2,3,4,8,9],sqlite_cursor:[0,2,3,4,8,9],sqlite_handl:[0,4],standard:[1,7],start:[0,4,9,10],start_dat:9,starting_bal:[0,10],starting_d:[0,10],state:10,statu:[0,9],still:10,store:8,str:[0,2,3,4,5,8,9,11],straightforward:10,string:[0,11],structur:10,sub:10,subaccount:[0,10,12],subaccount_id:0,submit:[7,10],sum:0,support:[3,7,10,12],tabl:3,table_nam:3,tag:[2,9],tag_nam:9,take:10,target:4,target_fil:4,tell:10,templat:9,template_account_root:9,template_root_account:[4,9],template_transact:4,test:7,text:9,them:[7,10],thi:[0,7,9,10],tied:9,time:9,timezon:[10,11],to_account:[9,10],to_sqlit:[0,2,3,4,8,9],tracker:[7,10],transact:[1,4,6,12],transaction_class:4,transaction_guid:9,transaction_nod:9,transactionmanag:[4,9,10],transfer:[9,10],tri:11,tupl:[0,3,9,10],turn:10,two:10,type:[0,2,3,4,5,8,9,10,11],tzinfo:10,unabl:4,uncompress:10,under:[0,7],underscor:0,union:[0,8],uniqu:[3,5],unit:7,unknown:3,unwieldi:10,updat:[3,10],upload:4,upper:10,uri:9,usag:10,usd:10,use:[4,10],use_gzip:[4,10],used:[0,2,3,5,8,9,10],user:[0,11],using:[4,7,10],util:[1,6],valu:[8,9],valueerror:0,variou:5,version:[2,6,7,10],via:10,view:10,void_reason:[9,12],void_tim:[9,12],wai:10,want:[0,9,10],were:9,what:[6,10],when:[4,9,10],where:[3,10],where_condit:3,where_paramet:3,which:[9,10],window:7,without:[10,11],world:10,would:10,write:[0,2,3,4,7,8,9,10],written:10,wrote:10,xml:[0,2,3,4,8,9,10],xml_obj:9,xml_object:9,yield:10,you:[0,7,9,10],your:[7,10]},titles:["Account","Code Documentation","Commodity","File Formats","GnuCash File","GUID Object","Welcome to gnewcash\u2019s documentation!","Overview","Slot","Transaction","Using GNewCash","Utils","Versions"],titleterms:{Using:10,account:[0,10],book:10,code:1,comment:10,commod:[2,10],compat:7,concern:10,creat:10,document:[1,6],file:[3,4],format:3,gnewcash:[6,7,10],gnucash:4,gnucashfil:10,guid:5,instal:7,interest:10,liabil:7,manag:10,object:5,overview:7,python:7,question:10,retriev:10,shortcut:0,simplifi:10,slot:8,special:0,standard:0,transact:[9,10],util:11,version:12,welcom:6,what:7}})