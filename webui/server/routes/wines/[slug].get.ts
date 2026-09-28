import { sourceWineUrl } from '#shared/catalog'

export default defineEventHandler(event => sendRedirect(event, sourceWineUrl(getRouterParam(event, 'slug') || ''), 308))
