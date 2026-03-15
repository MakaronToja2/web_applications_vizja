import strawberry
from strawberry.fastapi import GraphQLRouter
from gql.queries import Query
from gql.mutations import Mutation
from gql.subscriptions import Subscription

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
)

graphql_router = GraphQLRouter(schema)
