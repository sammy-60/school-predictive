function togglePw(){
  const el = document.getElementById('password');
  const btn = event.currentTarget;
  if(el.type === 'password'){
    el.type = 'text';
    btn.textContent = 'Hide';
  }else{
    el.type = 'password';
    btn.textContent = 'Show';
  }
}
