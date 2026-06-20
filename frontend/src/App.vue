<template>
  <header class="topbar">
    <RouterLink class="brand" to="/">quantop</RouterLink>
    <nav>
      <RouterLink to="/">总览</RouterLink>
      <RouterLink to="/market">市场</RouterLink>
      <RouterLink to="/factors">因子</RouterLink>
      <RouterLink to="/sync">同步</RouterLink>
    </nav>
  </header>
  <main>
    <RouterView />
  </main>
</template>
